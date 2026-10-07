# ruff: noqa: B008

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, aliased

from core.estoque import buscar_estoque_para_update
from core.security import exigir_perfil
from database.session import get_db
from models.devolucao import Devolucao, StatusDevolucaoEnum
from models.estoque_setor import EstoqueSetor, MovimentacaoEstoqueSetor
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem, StatusRequisicaoItemEnum
from models.setor import Setor
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


def _consulta_devolucoes():
    solicitante = aliased(Usuario)
    operador = aliased(Usuario)
    analista = aliased(Usuario)
    return (
        select(
            Devolucao.id.label("devolucao_id"),
            Devolucao.requisicao_item_id.label("requisicao_item_id"),
            Devolucao.status.label("status"),
            Devolucao.peso_total_g.label("peso_total_g"),
            Devolucao.peso_unitario_g.label("peso_unitario_g"),
            Devolucao.quantidade_calculada.label("quantidade_calculada"),
            Devolucao.observacao.label("observacao"),
            Devolucao.observacao_analise.label("observacao_analise"),
            Devolucao.created_at.label("created_at"),
            Devolucao.analisada_at.label("analisada_at"),
            RequisicaoItem.id.label("item_id"),
            RequisicaoItem.quantidade_solicitada.label("quantidade_solicitada"),
            RequisicaoItem.quantidade_atendida.label("quantidade_atendida"),
            RequisicaoItem.status.label("item_status"),
            Requisicao.id.label("requisicao_id"),
            Requisicao.numero.label("requisicao_numero"),
            Requisicao.setor_id.label("setor_id"),
            Requisicao.usuario_solicitante_id.label("usuario_solicitante_id"),
            Setor.nome.label("setor_nome"),
            Material.id.label("material_id"),
            Material.codigo.label("material_codigo"),
            Material.descricao.label("material_descricao"),
            solicitante.id.label("solicitante_id"),
            solicitante.nome.label("solicitante_nome"),
            operador.id.label("operador_id"),
            operador.nome.label("operador_nome"),
            analista.id.label("analista_id"),
            analista.nome.label("analista_nome"),
        )
        .select_from(Devolucao)
        .join(RequisicaoItem, RequisicaoItem.id == Devolucao.requisicao_item_id)
        .join(Requisicao, Requisicao.id == RequisicaoItem.requisicao_id)
        .join(Setor, Setor.id == Requisicao.setor_id)
        .join(Material, Material.id == RequisicaoItem.material_id)
        .join(solicitante, solicitante.id == Requisicao.usuario_solicitante_id)
        .join(operador, operador.id == Devolucao.usuario_operador_id)
        .outerjoin(analista, analista.id == Devolucao.usuario_analise_id)
    )


def _devolucao_completa(row) -> dict:
    analista = None
    if row["analista_id"] is not None:
        analista = {"id": row["analista_id"], "nome": row["analista_nome"]}
    return {
        "id": row["devolucao_id"],
        "requisicao_item_id": row["requisicao_item_id"],
        "status": row["status"],
        "peso_total_g": row["peso_total_g"],
        "peso_unitario_g": row["peso_unitario_g"],
        "quantidade_calculada": row["quantidade_calculada"],
        "observacao": row["observacao"],
        "observacao_analise": row["observacao_analise"],
        "created_at": row["created_at"],
        "analisada_at": row["analisada_at"],
        "item": {
            "id": row["item_id"],
            "quantidade_solicitada": row["quantidade_solicitada"],
            "quantidade_atendida": row["quantidade_atendida"],
            "status": row["item_status"],
            "material": {
                "id": row["material_id"],
                "codigo": row["material_codigo"],
                "descricao": row["material_descricao"],
            },
        },
        "requisicao": {
            "id": row["requisicao_id"],
            "numero": row["requisicao_numero"],
            "setor_id": row["setor_id"],
            "usuario_solicitante_id": row["usuario_solicitante_id"],
            "setor": {"id": row["setor_id"], "nome": row["setor_nome"]},
        },
        "solicitante": {
            "id": row["solicitante_id"],
            "nome": row["solicitante_nome"],
        },
        "operador": {"id": row["operador_id"], "nome": row["operador_nome"]},
        "analista": analista,
    }


@router.get("")
def listar_devolucoes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filtro: StatusDevolucaoEnum | None = Query(default=None, alias="status"),
    requisicao_id: int | None = Query(default=None, gt=0),
    requisicao_item_id: int | None = Query(default=None, gt=0),
    usuario_solicitante_id: int | None = Query(default=None, gt=0),
    usuario_operador_id: int | None = Query(default=None, gt=0),
    data_de: date | None = None,
    data_ate: date | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.gestor,
            PerfilEnum.admin,
        )
    ),
):
    if data_de is not None and data_ate is not None and data_de > data_ate:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Dados inválidos",
                "erros": [
                    {
                        "campo": "data_de",
                        "mensagem": "data_de não pode ser posterior a data_ate",
                    }
                ],
            },
        )

    query = _consulta_devolucoes()
    if status_filtro is not None:
        query = query.where(Devolucao.status == status_filtro)
    if requisicao_id is not None:
        query = query.where(Requisicao.id == requisicao_id)
    if requisicao_item_id is not None:
        query = query.where(RequisicaoItem.id == requisicao_item_id)
    if usuario_atual.perfil == PerfilEnum.solicitante:
        query = query.where(Requisicao.usuario_solicitante_id == usuario_atual.id)
    else:
        if usuario_solicitante_id is not None:
            query = query.where(
                Requisicao.usuario_solicitante_id == usuario_solicitante_id
            )
        if usuario_operador_id is not None:
            query = query.where(Devolucao.usuario_operador_id == usuario_operador_id)
    if data_de is not None:
        query = query.where(
            Devolucao.created_at >= datetime.combine(data_de, time.min)
        )
    if data_ate is not None:
        query = query.where(
            Devolucao.created_at <= datetime.combine(data_ate, time.max)
        )

    total = db.scalar(
        query.with_only_columns(func.count(Devolucao.id)).order_by(None)
    ) or 0
    rows = db.execute(
        query.order_by(Devolucao.created_at.desc(), Devolucao.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).mappings().all()
    return {
        "dados": [_devolucao_completa(row) for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_devolucao(
    payload: DevolucaoCreateRequest,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", min_length=1, max_length=128
    ),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)
    ),
):
    operador_id = usuario_atual.id
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key não pode estar vazia"
        )

    db.rollback()
    try:
        with db.begin():
            if db.scalar(
                select(Devolucao.id).where(Devolucao.idempotency_key == idempotency_key)
            ):
                raise HTTPException(
                    status_code=409, detail="Esta devolução já foi registrada"
                )

            item_ref = db.get(RequisicaoItem, payload.requisicao_item_id)
            if item_ref is None:
                raise HTTPException(
                    status_code=404, detail="Item de requisição não encontrado"
                )
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == item_ref.requisicao_id)
                .with_for_update()
            )
            item = db.scalar(
                select(RequisicaoItem)
                .where(
                    RequisicaoItem.id == payload.requisicao_item_id,
                    RequisicaoItem.requisicao_id == item_ref.requisicao_id,
                )
                .with_for_update()
            )
            if requisicao is None or item is None:
                raise HTTPException(
                    status_code=404, detail="Item de requisição não encontrado"
                )
            if (
                usuario_atual.perfil == PerfilEnum.solicitante
                and requisicao.usuario_solicitante_id != operador_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Você só pode devolver itens das suas requisições",
                )
            if (
                requisicao.status != StatusRequisicaoEnum.atendida
                or item.status != StatusRequisicaoItemEnum.atendido
            ):
                raise HTTPException(
                    status_code=409, detail="A devolução exige um item já atendido"
                )

            material = db.scalar(
                select(Material)
                .where(
                    Material.id == item.material_id,
                    Material.qr_code == payload.qr_code,
                    Material.ativo.is_(True),
                )
                .with_for_update()
            )
            if material is None:
                raise HTTPException(
                    status_code=404,
                    detail="QR Code não corresponde ao material do item",
                )
            if material.peso_unitario_g is None or material.peso_unitario_g <= 0:
                raise HTTPException(
                    status_code=409,
                    detail="Material sem peso unitário válido cadastrado",
                )

            quantidade = (payload.peso_total_g / material.peso_unitario_g).quantize(
                Decimal("0.001"),
                rounding=ROUND_HALF_UP,
            )
            if quantidade <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Peso insuficiente para calcular uma unidade devolvida",
                )
            quantidade_reservada = db.scalar(
                select(
                    func.coalesce(func.sum(Devolucao.quantidade_calculada), 0)
                ).where(
                    Devolucao.requisicao_item_id == item.id,
                    Devolucao.status.in_(
                        [StatusDevolucaoEnum.pendente, StatusDevolucaoEnum.aceita]
                    ),
                )
            ) or Decimal(0)
            disponivel = item.quantidade_atendida - quantidade_reservada
            if quantidade > disponivel:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "A quantidade pesada excede o saldo atendido ainda não devolvido",
                        "quantidade_disponivel": str(disponivel),
                        "quantidade_calculada": str(quantidade),
                    },
                )

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
        raise HTTPException(
            status_code=409,
            detail="Conflito ao registrar devolução; verifique a chave de idempotência",
        ) from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflito concorrente ao registrar devolução; tente novamente",
        ) from exc


@router.get("/pendentes")
def listar_devolucoes_pendentes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    query = select(Devolucao).where(Devolucao.status == StatusDevolucaoEnum.pendente)
    total = (
        db.scalar(
            select(func.count())
            .select_from(Devolucao)
            .where(
                Devolucao.status == StatusDevolucaoEnum.pendente,
            )
        )
        or 0
    )
    devolucoes = db.scalars(
        query.order_by(Devolucao.created_at, Devolucao.id)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "dados": [_devolucao_dict(item) for item in devolucoes],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{devolucao_id}")
def obter_devolucao(
    devolucao_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(
            PerfilEnum.solicitante,
            PerfilEnum.almoxarife,
            PerfilEnum.gestor,
            PerfilEnum.admin,
        )
    ),
):
    row = db.execute(
        _consulta_devolucoes().where(Devolucao.id == devolucao_id)
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Devolução não encontrada")
    if (
        usuario_atual.perfil == PerfilEnum.solicitante
        and row["usuario_solicitante_id"] != usuario_atual.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Você só pode consultar devoluções das suas requisições",
        )
    return _devolucao_completa(row)


@router.patch("/{devolucao_id}/aceitar")
def aceitar_devolucao(
    devolucao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
):
    db.rollback()
    try:
        with db.begin():
            devolucao_ref = db.get(Devolucao, devolucao_id)
            if devolucao_ref is None:
                raise HTTPException(status_code=404, detail="Devolução não encontrada")
            item_ref = db.get(RequisicaoItem, devolucao_ref.requisicao_item_id)
            if item_ref is None:
                raise HTTPException(
                    status_code=404, detail="Item da devolução não encontrado"
                )
            requisicao = db.scalar(
                select(Requisicao)
                .where(Requisicao.id == item_ref.requisicao_id)
                .with_for_update()
            )
            item = db.scalar(
                select(RequisicaoItem)
                .where(RequisicaoItem.id == item_ref.id)
                .with_for_update()
            )
            devolucao = db.scalar(
                select(Devolucao).where(Devolucao.id == devolucao_id).with_for_update()
            )
            if requisicao is None or item is None or devolucao is None:
                raise HTTPException(status_code=404, detail="Devolução não encontrada")
            if devolucao.status != StatusDevolucaoEnum.pendente:
                raise HTTPException(
                    status_code=409, detail="A devolução já foi analisada"
                )

            idempotency_key = f"devolucao:{devolucao.id}"
            if db.scalar(
                select(MovimentacaoEstoque.id).where(
                    MovimentacaoEstoque.idempotency_key == idempotency_key,
                )
            ):
                raise HTTPException(
                    status_code=409,
                    detail="O crédito desta devolução já foi registrado",
                )
            estoque = buscar_estoque_para_update(item.material_id, db)
            if estoque is None:
                raise HTTPException(
                    status_code=409,
                    detail="Não existe registro de estoque para este material",
                )

            anterior = estoque.quantidade_atual
            posterior = anterior + devolucao.quantidade_calculada
            estoque.quantidade_atual = posterior
            estoque.data_ultima_movimentacao = func.now()
            setor = db.scalar(select(Setor).where(Setor.id == requisicao.setor_id).with_for_update())
            saldo_setor = db.scalar(select(EstoqueSetor).where(EstoqueSetor.setor_id == requisicao.setor_id, EstoqueSetor.material_id == item.material_id).with_for_update())
            if setor is None or saldo_setor is None or saldo_setor.quantidade_atual < devolucao.quantidade_calculada:
                raise HTTPException(status_code=409, detail="Saldo do setor insuficiente para reconciliar a devolução")
            saldo_anterior_setor = saldo_setor.quantidade_atual
            saldo_setor.quantidade_atual -= devolucao.quantidade_calculada
            db.add(MovimentacaoEstoqueSetor(setor_id=requisicao.setor_id, material_id=item.material_id,
                usuario_id=usuario_atual.id, requisicao_id=requisicao.id, tipo="DEVOLUCAO_AO_ALMOXARIFADO",
                quantidade=devolucao.quantidade_calculada, saldo_anterior=saldo_anterior_setor,
                saldo_posterior=saldo_setor.quantidade_atual, idempotency_key=f"devolucao:{devolucao.id}:setor",
                observacao=f"Devolução {devolucao.id} aceita"))
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
        raise HTTPException(
            status_code=409, detail="Conflito ao aceitar devolução; tente novamente"
        ) from exc


@router.patch("/{devolucao_id}/rejeitar")
def rejeitar_devolucao(
    devolucao_id: int,
    payload: DevolucaoRejeitarRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)
    ),
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
                raise HTTPException(
                    status_code=409, detail="A devolução já foi analisada"
                )
            devolucao.status = StatusDevolucaoEnum.rejeitada
            devolucao.usuario_analise_id = usuario_atual.id
            devolucao.analisada_at = func.now()
            devolucao.observacao_analise = payload.motivo
            db.flush()
            return _devolucao_dict(devolucao)
    except HTTPException:
        db.rollback()
        raise
