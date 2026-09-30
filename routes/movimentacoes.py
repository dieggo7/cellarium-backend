# ruff: noqa: B008

from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.estoque import buscar_estoque_para_update
from core.security import exigir_perfil
from database.session import get_db
from models.estoque import Estoque
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.requisicao import Requisicao
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/movimentacoes", tags=["movimentações"])
router_materiais = APIRouter(prefix="/materiais", tags=["movimentações"])


class MovimentacaoCreateRequest(BaseModel):
    material_id: int = Field(gt=0)
    tipo: TipoMovimentacaoEnum
    quantidade: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=500)
    requisicao_id: int | None = Field(default=None, gt=0)


def _conditions(material_id: int | None, usuario_id: int | None, setor_id: int | None,
                requisicao_id: int | None, tipo: TipoMovimentacaoEnum | None,
                data_de: date | None, data_ate: date | None):
    clauses = []
    params: dict[str, object] = {}
    for column, value, key in (
        ("material_id", material_id, "material_id"),
        ("usuario_id", usuario_id, "usuario_id"),
        ("setor_id", setor_id, "setor_id"),
        ("requisicao_id", requisicao_id, "requisicao_id"),
    ):
        if value is not None:
            clauses.append(f"{column} = :{key}")
            params[key] = value
    if tipo is not None:
        clauses.append("tipo = :tipo")
        params["tipo"] = tipo.value
    if data_de is not None:
        clauses.append("data >= :data_de")
        params["data_de"] = datetime.combine(data_de, time.min)
    if data_ate is not None:
        clauses.append("data <= :data_ate")
        params["data_ate"] = datetime.combine(data_ate, time.max)
    return clauses, params


def _listar(db: Session, page: int, limit: int, clauses: list[str], params: dict[str, object]):
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(text("SELECT COUNT(*) FROM vw_historico_movimentacoes" + where), params).scalar_one()
    data_params = {**params, "limit": limit, "offset": (page - 1) * limit}
    rows = db.execute(text(
        "SELECT * FROM vw_historico_movimentacoes" + where
        + " ORDER BY data DESC, id DESC LIMIT :limit OFFSET :offset"
    ), data_params).mappings().all()
    return {"dados": [dict(row) for row in rows], "total": total, "page": page, "limit": limit}


def _filtros(page: int, limit: int, material_id: int | None, usuario_id: int | None,
             setor_id: int | None, requisicao_id: int | None, tipo: TipoMovimentacaoEnum | None,
             data_de: date | None, data_ate: date | None):
    if data_de is not None and data_ate is not None and data_de > data_ate:
        raise HTTPException(status_code=400, detail="data_de não pode ser posterior a data_ate")
    clauses, params = _conditions(material_id, usuario_id, setor_id, requisicao_id, tipo, data_de, data_ate)
    return page, limit, clauses, params


@router.get("")
def listar_movimentacoes(
    page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100),
    material_id: int | None = Query(default=None, gt=0), usuario_id: int | None = Query(default=None, gt=0),
    setor_id: int | None = Query(default=None, gt=0), requisicao_id: int | None = Query(default=None, gt=0),
    tipo: TipoMovimentacaoEnum | None = None, data_de: date | None = None, data_ate: date | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor, PerfilEnum.almoxarife)),
):
    page, limit, clauses, params = _filtros(page, limit, material_id, usuario_id, setor_id,
                                            requisicao_id, tipo, data_de, data_ate)
    return _listar(db, page, limit, clauses, params)


@router.get("/{movimentacao_id}")
def detalhe_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor, PerfilEnum.almoxarife)),
):
    row = db.execute(text("SELECT * FROM vw_historico_movimentacoes WHERE id = :id"), {"id": movimentacao_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    return dict(row)


@router_materiais.get("/{material_id}/movimentacoes")
def listar_movimentacoes_material(
    material_id: int,
    page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100),
    usuario_id: int | None = Query(default=None, gt=0), setor_id: int | None = Query(default=None, gt=0),
    requisicao_id: int | None = Query(default=None, gt=0), tipo: TipoMovimentacaoEnum | None = None,
    data_de: date | None = None, data_ate: date | None = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor, PerfilEnum.almoxarife)),
):
    if db.get(Material, material_id) is None:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    page, limit, clauses, params = _filtros(page, limit, material_id, usuario_id, setor_id,
                                            requisicao_id, tipo, data_de, data_ate)
    return _listar(db, page, limit, clauses, params)


@router.post("", status_code=status.HTTP_201_CREATED)
def criar_movimentacao(
    payload: MovimentacaoCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)),
):
    """Em AJUSTE, quantidade é o saldo alvo; a movimentação guarda a diferença absoluta."""
    usuario_id = usuario_atual.id
    if payload.tipo == TipoMovimentacaoEnum.saida:
        raise HTTPException(status_code=400, detail="SAIDA deve ser registrada pela separação da requisição")
    if payload.tipo == TipoMovimentacaoEnum.ajuste and not (payload.observacao and payload.observacao.strip()):
        raise HTTPException(status_code=400, detail="observacao é obrigatória para AJUSTE")
    if payload.tipo != TipoMovimentacaoEnum.ajuste and payload.quantidade <= 0:
        raise HTTPException(status_code=400, detail="quantidade deve ser maior que zero")
    if payload.requisicao_id is not None and payload.tipo != TipoMovimentacaoEnum.devolucao:
        raise HTTPException(status_code=400, detail="requisicao_id só pode ser informado para DEVOLUCAO")
    db.rollback()
    try:
        with db.begin():
            material = db.scalar(select(Material).where(Material.id == payload.material_id).with_for_update())
            if material is None or not material.ativo:
                raise HTTPException(status_code=404, detail="Material não encontrado ou inativo")
            if payload.requisicao_id is not None and db.get(Requisicao, payload.requisicao_id) is None:
                raise HTTPException(status_code=404, detail="Requisição não encontrada")
            estoque = buscar_estoque_para_update(payload.material_id, db)
            if estoque is None:
                if payload.tipo != TipoMovimentacaoEnum.entrada:
                    raise HTTPException(status_code=409, detail="Não existe registro de estoque para este material")
                estoque = Estoque(material_id=payload.material_id, quantidade_atual=Decimal(0),
                                  estoque_minimo=Decimal(0))
                db.add(estoque)
                db.flush()
            anterior = estoque.quantidade_atual
            if payload.tipo in {TipoMovimentacaoEnum.entrada, TipoMovimentacaoEnum.devolucao}:
                posterior = anterior + payload.quantidade
                quantidade_movimentada = payload.quantidade
            else:
                posterior = payload.quantidade
                quantidade_movimentada = abs(posterior - anterior)
                if quantidade_movimentada == 0:
                    raise HTTPException(status_code=400, detail="O saldo informado já é o saldo atual")
            if posterior < 0:
                raise HTTPException(status_code=409, detail="O saldo de estoque não pode ficar negativo")
            estoque.quantidade_atual = posterior
            estoque.data_ultima_movimentacao = func.now()
            movimentacao = MovimentacaoEstoque(
                material_id=payload.material_id,
                usuario_id=usuario_id,
                requisicao_id=payload.requisicao_id,
                tipo=payload.tipo,
                quantidade=quantidade_movimentada,
                estoque_anterior=anterior,
                estoque_posterior=posterior,
                observacao=payload.observacao,
            )
            db.add(movimentacao)
            db.flush()
            return {"id": movimentacao.id, "material_id": movimentacao.material_id,
                    "tipo": movimentacao.tipo, "quantidade": movimentacao.quantidade,
                    "estoque_anterior": anterior, "estoque_posterior": posterior,
                    "estoque_atual": posterior, "usuario_id": usuario_id,
                    "requisicao_id": payload.requisicao_id}
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao registrar movimentação; tente novamente") from exc