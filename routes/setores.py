# ruff: noqa: B008


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
from database.session import get_db
from models.setor import Setor
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/setores", tags=["setores"])


class SetorItem(BaseModel):
    id: int
    nome: str
    codigo: str
    ativo: bool


class SetorCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    codigo: str = Field(min_length=1, max_length=20)

    @field_validator("nome", "codigo")
    @classmethod
    def validar_texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatório")
        return value


class SetorUpdateRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    ativo: bool | None = None

    @field_validator("nome", "codigo")
    @classmethod
    def validar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Campo não pode ficar vazio")
        return value


def _salvar(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Nome ou código de setor já cadastrado") from exc


def _to_item(setor: Setor) -> SetorItem:
    return SetorItem(id=setor.id, nome=setor.nome, codigo=setor.codigo, ativo=setor.ativo)


@router.get("", response_model=list[SetorItem])
def list_setores(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    query = select(Setor)
    if apenas_ativos:
        query = query.where(Setor.ativo.is_(True))

    setores = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(s) for s in setores]


@router.get("/{setor_id}", response_model=SetorItem)
def get_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    setor = db.get(Setor, setor_id)
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    return _to_item(setor)


@router.post("", response_model=SetorItem, status_code=201)
def create_setor(
    payload: SetorCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    if db.scalar(select(Setor).where(Setor.codigo == payload.codigo)):
        raise HTTPException(status_code=409, detail="Código de setor já cadastrado")

    if db.scalar(select(Setor).where(Setor.nome == payload.nome)):
        raise HTTPException(status_code=409, detail="Nome de setor já cadastrado")

    setor = Setor(nome=payload.nome, codigo=payload.codigo, ativo=True)
    db.add(setor)
    _salvar(db)
    db.refresh(setor)

    return _to_item(setor)


@router.put("/{setor_id}", response_model=SetorItem)
def update_setor(
    setor_id: int,
    payload: SetorUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    setor = db.scalar(select(Setor).where(Setor.id == setor_id).with_for_update())
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")

    alteracoes = payload.model_dump(exclude_unset=True)
    if not alteracoes:
        raise HTTPException(status_code=400, detail="Informe ao menos um campo para atualizar")
    if (
        "nome" in alteracoes
        and alteracoes["nome"] != setor.nome
        and db.scalar(select(Setor.id).where(Setor.nome == alteracoes["nome"], Setor.id != setor_id))
    ):
        raise HTTPException(status_code=409, detail="Nome de setor já cadastrado")
    if (
        "codigo" in alteracoes
        and alteracoes["codigo"] != setor.codigo
        and db.scalar(select(Setor.id).where(Setor.codigo == alteracoes["codigo"], Setor.id != setor_id))
    ):
        raise HTTPException(status_code=409, detail="Código de setor já cadastrado")
    if payload.nome is not None:
        setor.nome = payload.nome
    if payload.codigo is not None:
        setor.codigo = payload.codigo
    if payload.ativo is not None:
        setor.ativo = payload.ativo

    _salvar(db)
    db.refresh(setor)

    return _to_item(setor)


@router.delete("/{setor_id}")
def delete_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    setor = db.get(Setor, setor_id)
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    setor.ativo = False
    _salvar(db)
    return {"message": "Setor desativado com sucesso"}