# ruff: noqa: B008

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil
from database.session import get_db
from models.estoque_setor import EstoqueSetor, MovimentacaoEstoqueSetor
from models.material import Material
from models.requisicao import Requisicao, StatusRequisicaoEnum
from models.requisicao_item import RequisicaoItem
from models.setor import Setor
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/estoque-setor", tags=["estoque por setor"])


class ConsumoRequest(BaseModel):
    material_id: int = Field(gt=0)
    quantidade: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)


def _setor(usuario: Usuario, setor_id: int | None) -> int:
    if usuario.perfil == PerfilEnum.solicitante:
        if usuario.setor_id is None:
            raise HTTPException(status_code=409, detail="Sua conta não possui setor cadastrado")
        return usuario.setor_id
    if setor_id is None:
        raise HTTPException(status_code=400, detail="setor_id é obrigatório")
    return setor_id


@router.get("")
def listar_estoque_setor(
    setor_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.almoxarife, PerfilEnum.gestor, PerfilEnum.admin)),
):
    setor = _setor(usuario, setor_id)
    rows = db.execute(
        select(EstoqueSetor, Material, UnidadeMedida.sigla)
        .join(Material, Material.id == EstoqueSetor.material_id)
        .join(UnidadeMedida, UnidadeMedida.id == Material.unidade_medida_id)
        .where(EstoqueSetor.setor_id == setor, Material.ativo.is_(True))
        .order_by(Material.descricao)
    ).all()
    return [{"id": balance.id, "setor_id": setor, "material_id": material.id, "codigo": material.codigo,
             "material": material.descricao, "unidade_medida_id": material.unidade_medida_id,
             "unidade_sigla": sigla, "quantidade_atual": balance.quantidade_atual,
             "updated_at": balance.updated_at} for balance, material, sigla in rows]


@router.get("/historico")
def historico_estoque_setor(
    setor_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante, PerfilEnum.almoxarife, PerfilEnum.gestor, PerfilEnum.admin)),
):
    setor = _setor(usuario, setor_id)
    rows = db.execute(
        select(MovimentacaoEstoqueSetor, Material).join(Material, Material.id == MovimentacaoEstoqueSetor.material_id)
        .where(MovimentacaoEstoqueSetor.setor_id == setor)
        .order_by(MovimentacaoEstoqueSetor.created_at.desc(), MovimentacaoEstoqueSetor.id.desc()).limit(100)
    ).all()
    return [{"id": movement.id, "material_id": material.id, "codigo": material.codigo,
             "material": material.descricao, "tipo": movement.tipo, "quantidade": movement.quantidade,
             "saldo_anterior": movement.saldo_anterior, "saldo_posterior": movement.saldo_posterior,
             "observacao": movement.observacao, "created_at": movement.created_at}
            for movement, material in rows]


@router.post("/consumos", status_code=201)
def consumir_estoque_setor(
    payload: ConsumoRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_perfil(PerfilEnum.solicitante)),
):
    setor_id = _setor(usuario, None)
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key não pode estar vazia")
    try:
        db.rollback()
        with db.begin():
            setor = db.scalar(select(Setor).where(Setor.id == setor_id).with_for_update())
            material = db.get(Material, payload.material_id)
            if setor is None or material is None or not material.ativo:
                raise HTTPException(status_code=404, detail="Setor ou material não encontrado")
            os_aberta = db.scalar(
                select(Requisicao.id)
                .join(RequisicaoItem, RequisicaoItem.requisicao_id == Requisicao.id)
                .where(
                    Requisicao.setor_id == setor_id,
                    Requisicao.status == StatusRequisicaoEnum.atendida,
                    Requisicao.os_encerrada_at.is_(None),
                    RequisicaoItem.material_id == payload.material_id,
                    RequisicaoItem.quantidade_atendida > 0,
                )
                .limit(1)
            )
            if os_aberta is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Feche a OS que utiliza este material antes de liberar uma retirada do saldo compartilhado",
                )
            if db.scalar(select(MovimentacaoEstoqueSetor.id).where(MovimentacaoEstoqueSetor.idempotency_key == key)):
                raise HTTPException(status_code=409, detail="Este consumo já foi registrado")
            balance = db.scalar(select(EstoqueSetor).where(EstoqueSetor.setor_id == setor_id, EstoqueSetor.material_id == payload.material_id).with_for_update())
            if balance is None or balance.quantidade_atual < payload.quantidade:
                raise HTTPException(status_code=409, detail="Saldo insuficiente no estoque do setor")
            before = balance.quantidade_atual
            after = before - payload.quantidade
            balance.quantidade_atual = after
            db.add(MovimentacaoEstoqueSetor(setor_id=setor_id, material_id=material.id, usuario_id=usuario.id,
                tipo="CONSUMO", quantidade=payload.quantidade, saldo_anterior=before, saldo_posterior=after,
                idempotency_key=key, observacao=payload.observacao))
            db.flush()
            return {"material_id": material.id, "quantidade_atual": after}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao registrar consumo") from exc
