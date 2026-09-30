# ruff: noqa: B008


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.unidade_medida import UnidadeMedida
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/unidades-medida", tags=["unidades de medida"])


class UnidadeMedidaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    sigla: str | None
    ativo: bool


class UnidadeMedidaCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=50)
    sigla: str | None = Field(default=None, max_length=10)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("nome é obrigatório")
        return value


class UnidadeMedidaUpdateRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=50)
    sigla: str | None = Field(default=None, max_length=10)
    ativo: bool | None = None

    @field_validator("nome")
    @classmethod
    def validar_nome_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("nome não pode ficar vazio")
        return value


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma unidade de medida com esse nome",
        ) from exc


@router.get("", response_model=list[UnidadeMedidaItem])
def list_unidades_medida(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
) -> list[UnidadeMedida]:
    query = select(UnidadeMedida)
    if apenas_ativos:
        query = query.where(UnidadeMedida.ativo.is_(True))
    query = query.order_by(UnidadeMedida.nome).offset((page - 1) * limit).limit(limit)
    return list(db.scalars(query).all())


@router.get("/{unidade_id}", response_model=UnidadeMedidaItem)
def get_unidade_medida(
    unidade_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
) -> UnidadeMedida:
    unidade = db.get(UnidadeMedida, unidade_id)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade de medida não encontrada")
    return unidade


@router.post("", response_model=UnidadeMedidaItem, status_code=201)
def create_unidade_medida(
    payload: UnidadeMedidaCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
) -> UnidadeMedida:
    unidade = UnidadeMedida(nome=payload.nome.strip(), sigla=payload.sigla, ativo=True)
    db.add(unidade)
    _commit_or_conflict(db)
    db.refresh(unidade)
    return unidade


@router.put("/{unidade_id}", response_model=UnidadeMedidaItem)
def update_unidade_medida(
    unidade_id: int,
    payload: UnidadeMedidaUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
) -> UnidadeMedida:
    unidade = db.get(UnidadeMedida, unidade_id)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade de medida não encontrada")
    alteracoes = payload.model_dump(exclude_unset=True)
    if "nome" in alteracoes and alteracoes["nome"] is not None:
        alteracoes["nome"] = alteracoes["nome"].strip()
    for campo, valor in alteracoes.items():
        setattr(unidade, campo, valor)
    _commit_or_conflict(db)
    db.refresh(unidade)
    return unidade


@router.delete("/{unidade_id}", status_code=204)
def delete_unidade_medida(
    unidade_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
) -> None:
    unidade = db.get(UnidadeMedida, unidade_id)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade de medida não encontrada")
    unidade.ativo = False
    db.commit()
