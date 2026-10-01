# ruff: noqa: B008

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import settings
from core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    needs_password_rehash,
    verify_password,
)
from database.session import get_db
from models.atendimento_almoxarifado import (
    AtendimentoAlmoxarifado,
    StatusAtendimentoEnum,
)
from models.setor import Setor
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


class LoginRequest(BaseModel):
    login: str
    senha: str


class UsuarioPayload(BaseModel):
    id: int
    nome: str
    login: str
    perfil: PerfilEnum
    setor_id: int | None = None
    ativo: bool
    setor: str | None = None
    atendimento_atual: dict | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioPayload


def autenticar_usuario(db: Session, login: str, senha: str):
    usuario = db.scalar(select(Usuario).where(Usuario.login == login))
    if not usuario:
        return None
    if not usuario.ativo:
        return None
    if not verify_password(senha, usuario.senha_hash):
        return None
    if needs_password_rehash(usuario.senha_hash):
        usuario.senha_hash = get_password_hash(senha)
        db.commit()
    return usuario


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, payload.login, payload.senha)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(usuario.id),
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "login": usuario.login,
            "perfil": usuario.perfil,
            "setor_id": usuario.setor_id,
            "ativo": usuario.ativo,
        },
    }


@router.get("/me", response_model=UsuarioPayload)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    usuario = get_current_user(token, db)

    setor = db.get(Setor, usuario.setor_id) if usuario.setor_id is not None else None
    atendimento_atual = None
    if usuario.perfil == PerfilEnum.almoxarife:
        atendimento = db.scalar(
            select(AtendimentoAlmoxarifado)
            .where(
                AtendimentoAlmoxarifado.usuario_id == usuario.id,
                AtendimentoAlmoxarifado.status == StatusAtendimentoEnum.aberto,
            )
            .order_by(AtendimentoAlmoxarifado.data_inicio.desc())
        )
        if atendimento is not None:
            setor_atendimento = db.get(Setor, atendimento.setor_id)
            atendimento_atual = {
                "id": atendimento.id,
                "setor_id": atendimento.setor_id,
                "setor": setor_atendimento.nome if setor_atendimento else None,
                "data_inicio": atendimento.data_inicio,
            }
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "login": usuario.login,
        "perfil": usuario.perfil,
        "setor_id": usuario.setor_id,
        "ativo": usuario.ativo,
        "setor": setor.nome if setor else None,
        "atendimento_atual": atendimento_atual,
    }


@router.post("/logout")
def logout(usuario_atual: Usuario = Depends(get_current_user)):
    return {"message": "Logout concluído. Descarte o token no cliente."}


@router.post("/refresh")
def refresh_token(usuario_atual: Usuario = Depends(get_current_user)):
    access_token = create_access_token(
        subject=str(usuario_atual.id),
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,
    }


@router.post("/login/form")
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    usuario = autenticar_usuario(db, form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    access_token = create_access_token(
        subject=str(usuario.id),
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}
