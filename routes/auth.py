import time
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import settings
from core.security import (
    create_access_token,
    get_password_hash,
    needs_password_rehash,
    verify_password,
)
from database.session import get_db
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)


def _user_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limit_failed_login(
    request: Request,
    window_seconds: int = 60,
    max_attempts: int = 5,
) -> None:
    client_ip = _user_ip(request)
    now = time.monotonic()
    attempts = _LOGIN_ATTEMPTS[client_ip]
    attempts[:] = [attempt for attempt in attempts if now - attempt < window_seconds]
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )
    attempts.append(now)


def _clear_login_attempts(request: Request) -> None:
    _LOGIN_ATTEMPTS.pop(_user_ip(request), None)


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
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _rate_limit_failed_login(request)
    usuario = autenticar_usuario(db, payload.login, payload.senha)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_login_attempts(request)
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
    from core.security import decode_access_token

    payload = decode_access_token(token)
    if payload is None or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.get(Usuario, int(payload["sub"]))
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "login": usuario.login,
        "perfil": usuario.perfil,
        "setor_id": usuario.setor_id,
        "ativo": usuario.ativo,
    }


@router.post("/login/form")
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    _rate_limit_failed_login(request)
    usuario = autenticar_usuario(db, form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    _clear_login_attempts(request)
    access_token = create_access_token(
        subject=str(usuario.id),
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}
