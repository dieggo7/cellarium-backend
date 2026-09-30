# ruff: noqa: B008

from decimal import Decimal
from typing import Any, cast

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from core.estoque import buscar_estoque_para_update
from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.estoque import Estoque
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem, StatusRequisicaoItemEnum
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/requisicoes", tags=["itens de requisição"])


class ItemCreateRequest(BaseModel):
    material_id: int = Field(gt=0)
    quantidade_solicitada: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)


class ItemUpdateRequest(BaseModel):
    quantidade_solicitada: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)


class SepararRequest(BaseModel):
    quantidade: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)


def _requisicao_para_edicao(db: Session, requisicao_id: int, usuario_id: int, perfil: PerfilEnum):
    requisicao = db.scalar(
        select(Requisicao).where(Requisicao.id == requisicao_id).with_for_update()
    )
    if requisicao is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    if perfil != PerfilEnum.admin and requisicao.usuario_solicitante_id != usuario_id:
        raise HTTPException(status_code=403, detail="Você só pode alterar suas próprias requisições")
    if requisicao.status != StatusRequisicaoEnum.pendente:
        raise HTTPException(status_code=409, detail="A requisição precisa estar PENDENTE")
    return requisicao


@router.get("/{requisicao_id}/itens")
def listar_itens_requisicao(
    requisicao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    if db.get(Requisicao, requisicao_id) is None:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    return obter_itens_requisicao(db, requisicao_id)


def obter_itens_requisicao(db: Session, requisicao_id: int) -> list[dict]:
    rows = db.execute(
        select(RequisicaoItem, Material.codigo, Material.descricao, UnidadeMedida.nome,
               UnidadeMedida.sigla, Estoque.quantidade_atual)
        .join(Material, Material.id == RequisicaoItem.material_id)
        .join(UnidadeMedida, UnidadeMedida.id == Material.unidade_medida_id)
        .outerjoin(Estoque, Estoque.material_id == Material.id)
        .where(RequisicaoItem.requisicao_id == requisicao_id)
        .order_by(Material.descricao)
    ).all()
    return [
        {
            "id": row[0].id,
            "material_id": row[0].material_id,
            "codigo": row[1],
            "descricao": row[2],
            "unidade": {"nome": row[3], "sigla": row[4]},
            "quantidade_solicitada": row[0].quantidade_solicitada,
            "quantidade_separada": row[0].quantidade_separada,
            "quantidade_atendida": row[0].quantidade_atendida,
            "quantidade_pendente": row[0].quantidade_solicitada - row[0].quantidade_separada,
            "status": row[0].status,
            "observacao": row[0].observacao,
            "estoque_atual": row[5],
        }
        for row in rows
    ]


@router.post("/{requisicao_id}/itens", status_code=status.HTTP_201_CREATED)
def criar_item_requisicao(
    requisicao_id: int,
    payload: ItemCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)),
):
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            _requisicao_para_edicao(db, requisicao_id, usuario_id, perfil)
            material = db.get(Material, payload.material_id)
            if material is None or not material.ativo:
                raise HTTPException(status_code=404, detail="Material não encontrado ou inativo")
            if db.scalar(select(RequisicaoItem.id).where(
                RequisicaoItem.requisicao_id == requisicao_id,
                RequisicaoItem.material_id == payload.material_id,
            )):
                raise HTTPException(status_code=409, detail="Este material já está na requisição")
            item = RequisicaoItem(
                requisicao_id=requisicao_id,
                material_id=payload.material_id,
                quantidade_solicitada=payload.quantidade_solicitada,
                quantidade_separada=Decimal(0),
                quantidade_atendida=Decimal(0),
                status=StatusRequisicaoItemEnum.pendente,
                observacao=payload.observacao,
            )
            db.add(item)
            db.flush()
            return {"id": item.id, "requisicao_id": requisicao_id, "material_id": item.material_id,
                    "quantidade_solicitada": item.quantidade_solicitada,
                    "quantidade_separada": item.quantidade_separada,
                    "quantidade_atendida": item.quantidade_atendida, "status": item.status,
                    "observacao": item.observacao}
    except HTTPException:
        db.rollback()
        raise


@router.put("/{requisicao_id}/itens/{item_id}")
def atualizar_item_requisicao(
    requisicao_id: int,
    item_id: int,
    payload: ItemUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)),
):
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="Informe ao menos um campo para atualizar")
    if "quantidade_solicitada" in payload.model_fields_set and payload.quantidade_solicitada is None:
        raise HTTPException(status_code=400, detail="quantidade_solicitada não pode ser nula")
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            _requisicao_para_edicao(db, requisicao_id, usuario_id, perfil)
            item = db.scalar(select(RequisicaoItem).where(
                RequisicaoItem.id == item_id,
                RequisicaoItem.requisicao_id == requisicao_id,
            ).with_for_update())
            if item is None:
                raise HTTPException(status_code=404, detail="Item não encontrado nesta requisição")
            if item.status != StatusRequisicaoItemEnum.pendente:
                raise HTTPException(status_code=409, detail="O item precisa estar PENDENTE")
            if payload.quantidade_solicitada is not None:
                if payload.quantidade_solicitada < item.quantidade_separada:
                    raise HTTPException(status_code=409, detail="A quantidade solicitada não pode ser menor que a já separada")
                item.quantidade_solicitada = payload.quantidade_solicitada
            if "observacao" in payload.model_fields_set:
                item.observacao = payload.observacao
            db.flush()
            return {"id": item.id, "requisicao_id": item.requisicao_id, "material_id": item.material_id,
                    "quantidade_solicitada": item.quantidade_solicitada,
                    "quantidade_separada": item.quantidade_separada,
                    "quantidade_atendida": item.quantidade_atendida, "status": item.status,
                    "observacao": item.observacao}
    except HTTPException:
        db.rollback()
        raise


@router.delete("/{requisicao_id}/itens/{item_id}")
def cancelar_item_requisicao(
    requisicao_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.admin)),
):
    usuario_id = usuario_atual.id
    perfil = usuario_atual.perfil
    db.rollback()
    try:
        with db.begin():
            _requisicao_para_edicao(db, requisicao_id, usuario_id, perfil)
            item = db.scalar(select(RequisicaoItem).where(
                RequisicaoItem.id == item_id,
                RequisicaoItem.requisicao_id == requisicao_id,
            ).with_for_update())
            if item is None:
                raise HTTPException(status_code=404, detail="Item não encontrado nesta requisição")
            if item.status != StatusRequisicaoItemEnum.pendente:
                raise HTTPException(status_code=409, detail="O item precisa estar PENDENTE")
            if item.quantidade_separada > 0:
                raise HTTPException(status_code=409, detail="Item com separação parcial não pode ser removido")
            quantidade_ativa = db.scalar(select(func.count()).select_from(RequisicaoItem).where(
                RequisicaoItem.requisicao_id == requisicao_id,
                RequisicaoItem.status != StatusRequisicaoItemEnum.cancelado,
            )) or 0
            if quantidade_ativa <= 1:
                raise HTTPException(status_code=409, detail="Não é possível remover o último item; cancele a requisição")
            item.status = StatusRequisicaoItemEnum.cancelado
            db.flush()
            return {"mensagem": "Item cancelado com sucesso", "id": item.id, "status": item.status}
    except HTTPException:
        db.rollback()
        raise


@router.patch("/{requisicao_id}/itens/{item_id}/separar")
def separar_item_requisicao(
    requisicao_id: int,
    item_id: int,
    payload: SepararRequest | None = Body(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=1, max_length=128),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.almoxarife, PerfilEnum.admin)),
):
    usuario_id = usuario_atual.id
    db.rollback()
    try:
        with db.begin():
            requisicao = db.scalar(
                select(Requisicao).where(Requisicao.id == requisicao_id).with_for_update()
            )
            if requisicao is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            item = db.scalar(select(RequisicaoItem).where(
                RequisicaoItem.id == item_id,
                RequisicaoItem.requisicao_id == requisicao_id,
            ).with_for_update())
            if item is None:
                raise HTTPException(status_code=404, detail="Item não encontrado nesta requisição")
            if idempotency_key and db.scalar(
                select(MovimentacaoEstoque.id).where(
                    MovimentacaoEstoque.idempotency_key == idempotency_key,
                ).with_for_update()
            ):
                raise HTTPException(status_code=409, detail="Esta tentativa de separação já foi processada")
            if requisicao.status != StatusRequisicaoEnum.em_separacao:
                raise HTTPException(status_code=409, detail="A requisição precisa estar EM_SEPARACAO")
            if item.status != StatusRequisicaoItemEnum.pendente:
                raise HTTPException(status_code=409, detail="O item já foi separado ou cancelado")
            restante = item.quantidade_solicitada - item.quantidade_separada
            quantidade = payload.quantidade if payload and payload.quantidade is not None else restante
            if quantidade <= 0 or quantidade > restante:
                raise HTTPException(status_code=400, detail="quantidade deve ser maior que zero e não exceder a quantidade pendente")
            if quantidade < restante and not idempotency_key:
                raise HTTPException(status_code=400, detail="Idempotency-Key é obrigatório para separação parcial")
            estoque = buscar_estoque_para_update(item.material_id, db)
            if estoque is None:
                raise HTTPException(status_code=409, detail="Não existe registro de estoque para este material")
            estoque_anterior = estoque.quantidade_atual
            if estoque_anterior < quantidade:
                raise HTTPException(status_code=409, detail={
                    "mensagem": "Estoque insuficiente para realizar a separação",
                    "estoque_atual": str(estoque_anterior),
                    "quantidade_pedida": str(quantidade),
                })
            estoque_posterior = estoque_anterior - quantidade
            stock_update = cast(CursorResult[Any], db.execute(
                update(Estoque)
                .where(
                    Estoque.id == estoque.id,
                    Estoque.quantidade_atual == estoque_anterior,
                    Estoque.quantidade_atual >= quantidade,
                )
                .values(
                    quantidade_atual=estoque_posterior,
                    data_ultima_movimentacao=func.now(),
                )
                .execution_options(synchronize_session=False)
            ))
            if stock_update.rowcount != 1:
                raise HTTPException(status_code=409, detail="O saldo mudou durante a separação; recarregue e tente novamente")
            quantidade_separada_nova = item.quantidade_separada + quantidade
            status_item_novo = (
                StatusRequisicaoItemEnum.separado
                if quantidade_separada_nova >= item.quantidade_solicitada
                else StatusRequisicaoItemEnum.pendente
            )
            item_update = cast(CursorResult[Any], db.execute(
                update(RequisicaoItem)
                .where(
                    RequisicaoItem.id == item_id,
                    RequisicaoItem.requisicao_id == requisicao_id,
                    RequisicaoItem.status == StatusRequisicaoItemEnum.pendente,
                    RequisicaoItem.quantidade_separada == item.quantidade_separada,
                )
                .values(
                    quantidade_separada=quantidade_separada_nova,
                    status=status_item_novo,
                )
                .execution_options(synchronize_session=False)
            ))
            if item_update.rowcount != 1:
                raise HTTPException(status_code=409, detail="O item mudou durante a separação; recarregue e tente novamente")
            db.refresh(item)
            db.refresh(estoque)
            db.add(MovimentacaoEstoque(
                material_id=item.material_id,
                usuario_id=usuario_id,
                requisicao_id=requisicao_id,
                tipo=TipoMovimentacaoEnum.saida,
                idempotency_key=idempotency_key,
                quantidade=quantidade,
                estoque_anterior=estoque_anterior,
                estoque_posterior=estoque_posterior,
                observacao=item.observacao,
            ))
            requisicao.usuario_separador_id = usuario_id
            db.flush()
            itens_pendentes = db.scalar(select(func.count()).select_from(RequisicaoItem).where(
                RequisicaoItem.requisicao_id == requisicao_id,
                RequisicaoItem.status != StatusRequisicaoItemEnum.cancelado,
                RequisicaoItem.status != StatusRequisicaoItemEnum.separado,
            ))
            if itens_pendentes == 0:
                requisicao.status = StatusRequisicaoEnum.separada
            db.flush()
            return {
                "item": {"id": item.id, "material_id": item.material_id,
                         "quantidade_solicitada": item.quantidade_solicitada,
                         "quantidade_separada": item.quantidade_separada,
                         "quantidade_atendida": item.quantidade_atendida, "status": item.status},
                "estoque_atual": estoque.quantidade_atual,
                "status_requisicao": requisicao.status,
            }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esta tentativa de separação já foi processada") from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito concorrente na separação; tente novamente") from exc