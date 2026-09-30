from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
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
    nome: str
    codigo: str


class SetorUpdateRequest(BaseModel):
    nome: Optional[str] = None
    codigo: Optional[str] = None
    ativo: Optional[bool] = None


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
        query = query.where(Setor.ativo == True)  # noqa: E712

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
        raise HTTPException(status_code=400, detail="Código de setor já cadastrado")

    if db.scalar(select(Setor).where(Setor.nome == payload.nome)):
        raise HTTPException(status_code=400, detail="Nome de setor já cadastrado")

    setor = Setor(nome=payload.nome, codigo=payload.codigo, ativo=True)
    db.add(setor)
    db.commit()
    db.refresh(setor)

    return _to_item(setor)


@router.put("/{setor_id}", response_model=SetorItem)
def update_setor(
    setor_id: int,
    payload: SetorUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    setor = db.get(Setor, setor_id)
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")

    if payload.nome is not None:
        setor.nome = payload.nome
    if payload.codigo is not None:
        setor.codigo = payload.codigo
    if payload.ativo is not None:
        setor.ativo = payload.ativo

    db.commit()
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
    db.commit()
    return {"message": "Setor desativado com sucesso"}
