from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.session import get_db
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioItem(BaseModel):
    id: int
    nome: str
    login: str
    perfil: PerfilEnum
    setor_id: Optional[int] = None
    ativo: bool


class UsuarioCreateRequest(BaseModel):
    nome: str
    login: str
    senha: str
    perfil: PerfilEnum = PerfilEnum.solicitante
    setor_id: Optional[int] = None


class UsuarioUpdateRequest(BaseModel):
    nome: Optional[str] = None
    login: Optional[str] = None
    perfil: Optional[PerfilEnum] = None
    setor_id: Optional[int] = None
    ativo: Optional[bool] = None


def _to_item(usuario: Usuario) -> UsuarioItem:
    return UsuarioItem(
        id=usuario.id,
        nome=usuario.nome,
        login=usuario.login,
        perfil=usuario.perfil,
        setor_id=usuario.setor_id,
        ativo=usuario.ativo,
    )


@router.get("", response_model=list[UsuarioItem])
def list_usuarios(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    query = select(Usuario)
    if apenas_ativos:
        query = query.where(Usuario.ativo == True)  # noqa: E712

    usuarios = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioItem)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return _to_item(usuario)


@router.post("", response_model=UsuarioItem, status_code=201)
def create_usuario(payload: UsuarioCreateRequest, db: Session = Depends(get_db)):
    if db.scalar(select(Usuario).where(Usuario.login == payload.login)):
        raise HTTPException(status_code=400, detail="Login já cadastrado")

    from core.security import get_password_hash

    novo_usuario = Usuario(
        nome=payload.nome,
        login=payload.login,
        senha_hash=get_password_hash(payload.senha),
        perfil=payload.perfil,
        setor_id=payload.setor_id,
        ativo=True,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return _to_item(novo_usuario)


@router.put("/{usuario_id}", response_model=UsuarioItem)
def update_usuario(usuario_id: int, payload: UsuarioUpdateRequest, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if payload.nome is not None:
        usuario.nome = payload.nome
    if payload.login is not None:
        usuario.login = payload.login
    if payload.perfil is not None:
        usuario.perfil = payload.perfil
    if payload.setor_id is not None:
        usuario.setor_id = payload.setor_id
    if payload.ativo is not None:
        usuario.ativo = payload.ativo

    db.commit()
    db.refresh(usuario)

    return _to_item(usuario)


@router.delete("/{usuario_id}")
def delete_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    usuario.ativo = False  # soft delete, conforme combinado no AGENTS.md
    db.commit()
    return {"message": "Usuário desativado com sucesso"}