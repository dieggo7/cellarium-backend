# ruff: noqa: B008

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.estoque import buscar_estoque_para_update
from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.categoria import Categoria
from models.estoque import Estoque
from models.localizacao import Localizacao
from models.material import Material
from models.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacaoEnum
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/estoque", tags=["estoque"])


class SituacaoEstoque(str):
    NORMAL = "NORMAL"
    ESTOQUE_BAIXO = "ESTOQUE_BAIXO"
    SEM_ESTOQUE = "SEM_ESTOQUE"


class EstoqueCreateRequest(BaseModel):
    material_id: int = Field(gt=0)
    estoque_minimo: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    estoque_maximo: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    localizacao_id: int | None = Field(default=None, gt=0)
    lote: str | None = Field(default=None, max_length=50)
    quantidade_inicial: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=3)


class EstoqueUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estoque_minimo: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    estoque_maximo: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    localizacao_id: int | None = Field(default=None, gt=0)
    lote: str | None = Field(default=None, max_length=50)
    quantidade_atual: Decimal | None = None


def _detalhe(db: Session, estoque_id: int) -> dict:
    row = db.execute(
        select(
            Estoque,
            Material.codigo,
            Material.descricao,
            Categoria.id,
            Categoria.nome,
            UnidadeMedida.id,
            UnidadeMedida.nome,
            UnidadeMedida.sigla,
            Localizacao.id,
            Localizacao.codigo,
            Localizacao.descricao,
        )
        .join(Material, Material.id == Estoque.material_id)
        .join(Categoria, Categoria.id == Material.categoria_id)
        .join(UnidadeMedida, UnidadeMedida.id == Material.unidade_medida_id)
        .outerjoin(Localizacao, Localizacao.id == Estoque.localizacao_id)
        .where(Estoque.id == estoque_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Registro de estoque não encontrado")
    estoque = row[0]
    if estoque.quantidade_atual <= 0:
        situacao = SituacaoEstoque.SEM_ESTOQUE
    elif estoque.quantidade_atual <= estoque.estoque_minimo:
        situacao = SituacaoEstoque.ESTOQUE_BAIXO
    else:
        situacao = SituacaoEstoque.NORMAL
    return {
        "estoque_id": estoque.id,
        "material_id": estoque.material_id,
        "codigo": row[1],
        "material": row[2],
        "categoria_id": row[3],
        "categoria": row[4],
        "unidade_medida_id": row[5],
        "unidade": row[6],
        "unidade_sigla": row[7],
        "localizacao_id": row[8],
        "localizacao_codigo": row[9],
        "localizacao_descricao": row[10],
        "estoque_atual": estoque.quantidade_atual,
        "estoque_minimo": estoque.estoque_minimo,
        "estoque_maximo": estoque.estoque_maximo,
        "lote": estoque.lote,
        "data_ultima_movimentacao": estoque.data_ultima_movimentacao,
        "situacao": situacao,
    }


@router.get("")
def listar_estoque(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    busca: str | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    situacao: str | None = None,
    localizacao_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    valid_situations = {SituacaoEstoque.NORMAL, SituacaoEstoque.ESTOQUE_BAIXO, SituacaoEstoque.SEM_ESTOQUE}
    if situacao is not None and situacao not in valid_situations:
        raise HTTPException(status_code=400, detail="situacao deve ser NORMAL, ESTOQUE_BAIXO ou SEM_ESTOQUE")
    clauses = []
    params: dict[str, object] = {}
    if busca:
        clauses.append("(codigo LIKE :busca OR material LIKE :busca)")
        params["busca"] = f"%{busca.strip()}%"
    if categoria_id is not None:
        clauses.append("categoria_id = :categoria_id")
        params["categoria_id"] = categoria_id
    if situacao is not None:
        clauses.append("situacao = :situacao")
        params["situacao"] = situacao
    if localizacao_id is not None:
        clauses.append("localizacao_id = :localizacao_id")
        params["localizacao_id"] = localizacao_id
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(text("SELECT COUNT(*) FROM vw_estoque_atual" + where), params).scalar_one()
    result = db.execute(
        text("SELECT * FROM vw_estoque_atual" + where + " ORDER BY material, codigo LIMIT :limit OFFSET :offset"),
        {**params, "limit": limit, "offset": (page - 1) * limit},
    ).mappings().all()
    return {"dados": [dict(row) for row in result], "total": total, "page": page, "limit": limit}


@router.get("/material/{material_id}")
def obter_estoque_material(
    material_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    estoque = db.scalar(select(Estoque.id).where(Estoque.material_id == material_id))
    if estoque is None:
        raise HTTPException(status_code=404, detail="Material existe, mas não possui registro de estoque")
    return _detalhe(db, estoque)


@router.get("/{estoque_id}")
def obter_estoque(
    estoque_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    return _detalhe(db, estoque_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def criar_estoque(
    payload: EstoqueCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)),
):
    usuario_id = usuario_atual.id
    if payload.estoque_maximo is not None and payload.estoque_maximo < payload.estoque_minimo:
        raise HTTPException(status_code=400, detail="estoque_maximo não pode ser menor que estoque_minimo")
    db.rollback()
    try:
        with db.begin():
            material = db.scalar(select(Material).where(Material.id == payload.material_id).with_for_update())
            if material is None or not material.ativo:
                raise HTTPException(status_code=404, detail="Material não encontrado ou inativo")
            if buscar_estoque_para_update(payload.material_id, db) is not None:
                raise HTTPException(status_code=409, detail="Já existe registro de estoque para este material")
            if payload.localizacao_id is not None:
                localizacao = db.scalar(
                    select(Localizacao).where(Localizacao.id == payload.localizacao_id).with_for_update()
                )
                if localizacao is None or not localizacao.ativo:
                    raise HTTPException(status_code=404, detail="Localização não encontrada ou inativa")
            estoque = Estoque(
                material_id=payload.material_id,
                quantidade_atual=Decimal(0),
                estoque_minimo=payload.estoque_minimo,
                estoque_maximo=payload.estoque_maximo,
                localizacao_id=payload.localizacao_id,
                lote=payload.lote,
            )
            db.add(estoque)
            db.flush()
            if payload.quantidade_inicial > 0:
                estoque.quantidade_atual = payload.quantidade_inicial
                estoque.data_ultima_movimentacao = func.now()
                db.add(MovimentacaoEstoque(
                    material_id=payload.material_id,
                    usuario_id=usuario_id,
                    tipo=TipoMovimentacaoEnum.entrada,
                    quantidade=payload.quantidade_inicial,
                    estoque_anterior=Decimal(0),
                    estoque_posterior=payload.quantidade_inicial,
                    observacao="Saldo inicial",
                ))
            db.flush()
            return _detalhe(db, estoque.id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao criar registro de estoque") from exc


@router.put("/{estoque_id}")
def atualizar_estoque(
    estoque_id: int,
    payload: EstoqueUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.almoxarife)),
):
    if "quantidade_atual" in payload.model_fields_set:
        raise HTTPException(status_code=400, detail="O saldo só pode ser alterado por movimentação de estoque")
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="Informe ao menos um campo para atualizar")
    if "estoque_minimo" in payload.model_fields_set and payload.estoque_minimo is None:
        raise HTTPException(status_code=400, detail="estoque_minimo não pode ser nulo")
    db.rollback()
    try:
        with db.begin():
            estoque = db.scalar(
                select(Estoque).where(Estoque.id == estoque_id).with_for_update()
            )
            if estoque is None:
                raise HTTPException(status_code=404, detail="Registro de estoque não encontrado")
            changes = payload.model_dump(exclude_unset=True, exclude={"quantidade_atual"})
            minimo = changes.get("estoque_minimo", estoque.estoque_minimo)
            maximo = changes.get("estoque_maximo", estoque.estoque_maximo)
            if maximo is not None and maximo < minimo:
                raise HTTPException(status_code=400, detail="estoque_maximo não pode ser menor que estoque_minimo")
            if "localizacao_id" in changes and changes["localizacao_id"] is not None:
                localizacao = db.scalar(
                    select(Localizacao).where(Localizacao.id == changes["localizacao_id"]).with_for_update()
                )
                if localizacao is None or not localizacao.ativo:
                    raise HTTPException(status_code=404, detail="Localização não encontrada ou inativa")
            for field, value in changes.items():
                setattr(estoque, field, value)
            db.flush()
            return _detalhe(db, estoque.id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao atualizar registro de estoque") from exc


@router.delete("/{estoque_id}")
def excluir_estoque(
    estoque_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    db.rollback()
    try:
        with db.begin():
            estoque = db.scalar(select(Estoque).where(Estoque.id == estoque_id).with_for_update())
            if estoque is None:
                raise HTTPException(status_code=404, detail="Registro de estoque não encontrado")
            if estoque.quantidade_atual != 0:
                raise HTTPException(status_code=409, detail="Só é possível excluir estoque com saldo zero")
            db.delete(estoque)
            db.flush()
            return {"message": "Registro de estoque excluído com sucesso"}
    except HTTPException:
        db.rollback()
        raise