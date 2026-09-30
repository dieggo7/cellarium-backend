from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import exigir_perfil, get_current_user
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
    nome: str = Field(..., min_length=1, max_length=150)
    login: str = Field(..., min_length=1, max_length=50)
    senha: str = Field(..., min_length=1, max_length=512)
    perfil: PerfilEnum = PerfilEnum.solicitante
    setor_id: Optional[int] = None

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 512:
            raise ValueError("A senha deve ter no máximo 512 bytes UTF-8")
        return value


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
    usuario_atual: Usuario = Depends(get_current_user),  # exige estar logado, qualquer perfil
):
    query = select(Usuario)
    if apenas_ativos:
        query = query.where(Usuario.ativo == True)  # noqa: E712

    usuarios = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return [_to_item(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioItem)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return _to_item(usuario)


@router.post("", response_model=UsuarioItem, status_code=201)
def create_usuario(
    payload: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    if usuario_atual.perfil == PerfilEnum.gestor and payload.perfil == PerfilEnum.admin:
        raise HTTPException(
            status_code=403,
            detail="Gestor não pode criar usuários administradores",
        )
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
def update_usuario(
    usuario_id: int,
    payload: UsuarioUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario_atual.perfil == PerfilEnum.gestor and (
        usuario.perfil == PerfilEnum.admin or payload.perfil == PerfilEnum.admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Gestor não pode alterar usuários administrativos",
        )

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
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfil(PerfilEnum.admin)),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    usuario.ativo = False
    db.commit()
    return {"message": "Usuário desativado com sucesso"}
