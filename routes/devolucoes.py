# ruff: noqa: B008

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from core.estoque import buscar_estoque_para_update
from core.security import exigir_perfil
from database.session import get_db
from models.devolucao import Devolucao, StatusDevolucaoEnum
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem, StatusRequisicaoItemEnum
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/devolucoes", tags=["devoluções"])


class DevolucaoCreateRequest(BaseModel):
    requisicao_item_id: int = Field(gt=0)
    qr_code: str = Field(min_length=1, max_length=36)
    peso_total_g: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)

    @field_validator("qr_code")
    @classmethod
    def limpar_qr_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("QR Code obrigatório")
        return value


class DevolucaoRejeitarRequest(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)

    @field_validator("motivo")
    @classmethod
    def limpar_motivo(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Motivo obrigatório")
        return value


def _devolucao_dict(devolucao: Devolucao) -> dict:
    return {
        "id": devolucao.id,
        "requisicao_item_id": devolucao.requisicao_item_id,
        "usuario_operador_id": devolucao.usuario_operador_id,
        "usuario_analise_id": devolucao.usuario_analise_id,
        "peso_total_g": devolucao.peso_total_g,
        "peso_unitario_g": devolucao.peso_unitario_g,
        "quantidade_calculada": devolucao.quantidade_calculada,
        "status": devolucao.status,
        "observacao": devolucao.observacao,
        "observacao_analise": devolucao.observacao_analise,
        "created_at": devolucao.created_at,
        "analisada_at": devolucao.analisada_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_devolucao(
    payload: DevolucaoCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)),
):
    operador_id = usuario_atual.id
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key não pode estar vazia")

    db.rollback()
    try:
        with db.begin():
            if db.scalar(select(Devolucao.id).where(Devolucao.idempotency_key == idempotency_key)):
                raise HTTPException(status_code=409, detail="Esta devolução já foi registrada")

            item_ref = db.get(RequisicaoItem, payload.requisicao_item_id)
            if item_ref is None:
                raise HTTPException(status_code=404, detail="Item de requisição não encontrado")
            requisicao = db.scalar(
                select(Requisicao).where(Requisicao.id == item_ref.requisicao_id).with_for_update()
            )
            item = db.scalar(
                select(RequisicaoItem).where(
                    RequisicaoItem.id == payload.requisicao_item_id,
                    RequisicaoItem.requisicao_id == item_ref.requisicao_id,
                ).with_for_update()
            )
            if requisicao is None or item is None:
                raise HTTPException(status_code=404, detail="Item de requisição não encontrado")
            if usuario_atual.perfil == PerfilEnum.solicitante and requisicao.usuario_solicitante_id != operador_id:
                raise HTTPException(status_code=403, detail="Você só pode devolver itens das suas requisições")
            if requisicao.status != StatusRequisicaoEnum.atendida or item.status != StatusRequisicaoItemEnum.atendido:
                raise HTTPException(status_code=409, detail="A devolução exige um item já atendido")

            material = db.scalar(
                select(Material).where(
                    Material.id == item.material_id,
                    Material.qr_code == payload.qr_code,
                    Material.ativo.is_(True),
                ).with_for_update()
            )
            if material is None:
                raise HTTPException(status_code=404, detail="QR Code não corresponde ao material do item")
            if material.peso_unitario_g is None or material.peso_unitario_g <= 0:
                raise HTTPException(status_code=409, detail="Material sem peso unitário válido cadastrado")

            quantidade = (payload.peso_total_g / material.peso_unitario_g).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP,
            )
            if quantidade <= 0:
                raise HTTPException(status_code=400, detail="Peso insuficiente para calcular uma unidade devolvida")
            quantidade_reservada = db.scalar(
                select(func.coalesce(func.sum(Devolucao.quantidade_calculada), 0)).where(
                    Devolucao.requisicao_item_id == item.id,
                    Devolucao.status.in_([StatusDevolucaoEnum.pendente, StatusDevolucaoEnum.aceita]),
                )
            ) or Decimal(0)
            disponivel = item.quantidade_atendida - quantidade_reservada
            if quantidade > disponivel:
                raise HTTPException(status_code=409, detail={
                    "mensagem": "A quantidade pesada excede o saldo atendido ainda não devolvido",
                    "quantidade_disponivel": str(disponivel),
                    "quantidade_calculada": str(quantidade),
                })

            devolucao = Devolucao(
                requisicao_item_id=item.id,
                usuario_operador_id=operador_id,
                idempotency_key=idempotency_key,
                peso_total_g=payload.peso_total_g,
                peso_unitario_g=material.peso_unitario_g,
                quantidade_calculada=quantidade,
                status=StatusDevolucaoEnum.pendente,
                observacao=payload.observacao,
            )
            db.add(devolucao)
            db.flush()
            resultado = _devolucao_dict(devolucao)
        return resultado
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao registrar devolução; verifique a chave de idempotência") from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito concorrente ao registrar devolução; tente novamente") from exc


@router.get("/pendentes")
def listar_devolucoes_pendentes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)),
):
    query = select(Devolucao).where(Devolucao.status == StatusDevolucaoEnum.pendente)
    total = db.scalar(select(func.count()).select_from(Devolucao).where(
        Devolucao.status == StatusDevolucaoEnum.pendente,
    )) or 0
    devolucoes = db.scalars(
        query.order_by(Devolucao.created_at, Devolucao.id)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {"dados": [_devolucao_dict(item) for item in devolucoes], "total": total, "page": page, "limit": limit}


@router.patch("/{devolucao_id}/aceitar")
def aceitar_devolucao(
    devolucao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)),
):
    db.rollback()
    try:
        with db.begin():
            devolucao_ref = db.get(Devolucao, devolucao_id)
            if devolucao_ref is None:
                raise HTTPException(status_code=404, detail="Devolução não encontrada")
            item_ref = db.get(RequisicaoItem, devolucao_ref.requisicao_item_id)
            if item_ref is None:
                raise HTTPException(status_code=404, detail="Item da devolução não encontrado")
            requisicao = db.scalar(
                select(Requisicao).where(Requisicao.id == item_ref.requisicao_id).with_for_update()
            )
            item = db.scalar(
                select(RequisicaoItem).where(RequisicaoItem.id == item_ref.id).with_for_update()
            )
            devolucao = db.scalar(
                select(Devolucao).where(Devolucao.id == devolucao_id).with_for_update()
            )
            if requisicao is None or item is None or devolucao is None:
                raise HTTPException(status_code=404, detail="Devolução não encontrada")
            if devolucao.status != StatusDevolucaoEnum.pendente:
                raise HTTPException(status_code=409, detail="A devolução já foi analisada")

            idempotency_key = f"devolucao:{devolucao.id}"
            if db.scalar(select(MovimentacaoEstoque.id).where(
                MovimentacaoEstoque.idempotency_key == idempotency_key,
            )):
                raise HTTPException(status_code=409, detail="O crédito desta devolução já foi registrado")
            estoque = buscar_estoque_para_update(item.material_id, db)
            if estoque is None:
                raise HTTPException(status_code=409, detail="Não existe registro de estoque para este material")

            anterior = estoque.quantidade_atual
            posterior = anterior + devolucao.quantidade_calculada
            estoque.quantidade_atual = posterior
            estoque.data_ultima_movimentacao = func.now()
            movimentacao = MovimentacaoEstoque(
                material_id=item.material_id,
                usuario_id=usuario_atual.id,
                requisicao_id=requisicao.id,
                idempotency_key=idempotency_key,
                tipo=TipoMovimentacaoEnum.devolucao,
                quantidade=devolucao.quantidade_calculada,
                estoque_anterior=anterior,
                estoque_posterior=posterior,
                observacao=f"Devolução {devolucao.id} aceita; pesagem {devolucao.peso_total_g} g",
            )
            db.add(movimentacao)
            devolucao.status = StatusDevolucaoEnum.aceita
            devolucao.usuario_analise_id = usuario_atual.id
            devolucao.analisada_at = func.now()
            db.flush()
            resultado = {
                **_devolucao_dict(devolucao),
                "movimentacao_id": movimentacao.id,
                "estoque_anterior": anterior,
                "estoque_atual": posterior,
            }
        return resultado
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao aceitar devolução; tente novamente") from exc


@router.patch("/{devolucao_id}/rejeitar")
def rejeitar_devolucao(
    devolucao_id: int,
    payload: DevolucaoRejeitarRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)),
):
    db.rollback()
    try:
        with db.begin():
            devolucao = db.scalar(
                select(Devolucao).where(Devolucao.id == devolucao_id).with_for_update()
            )
            if devolucao is None:
                raise HTTPException(status_code=404, detail="Devolução não encontrada")
            if devolucao.status != StatusDevolucaoEnum.pendente:
                raise HTTPException(status_code=409, detail="A devolução já foi analisada")
            devolucao.status = StatusDevolucaoEnum.rejeitada
            devolucao.usuario_analise_id = usuario_atual.id
            devolucao.analisada_at = func.now()
            devolucao.observacao_analise = payload.motivo
            db.flush()
            return _devolucao_dict(devolucao)
    except HTTPException:
        db.rollback()
        raise
