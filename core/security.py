"""Password hashing, JWT validation and authorization dependencies."""

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from config.settings import settings
from database.session import get_db
from models.usuario import PerfilEnum, Usuario

password_hash = PasswordHash.recommended()  # Argon2id for new passwords.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_MAX_PASSWORD_BYTES = 1024
_MAX_TOKEN_CHARS = 4096
_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")
_USER_ID_PATTERN = re.compile(r"[1-9][0-9]{0,18}\Z")


def get_password_hash(senha_plana: str) -> str:
    if not senha_plana or len(senha_plana.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError("A senha deve conter entre 1 e 1024 bytes UTF-8")
    return password_hash.hash(senha_plana)


def verify_password(senha_plana: str, senha_hash: str) -> bool:
    if not senha_plana or len(senha_plana.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        return False

    try:
        if senha_hash.startswith("$argon2id$"):
            return password_hash.verify(senha_plana, senha_hash)
        if senha_hash.startswith(_BCRYPT_PREFIXES):
            # Old rows were hashed after truncation at 72 UTF-8 bytes. Refuse
            # longer input so that different passwords cannot share that prefix.
            senha_bytes = senha_plana.encode("utf-8")
            if len(senha_bytes) > 72:
                return False
            return bcrypt.checkpw(senha_bytes, senha_hash.encode("ascii"))
    except (ValueError, TypeError, UnknownHashError):
        return False
    return False


def needs_password_rehash(senha_hash: str) -> bool:
    return senha_hash.startswith(_BCRYPT_PREFIXES)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if not subject or not isinstance(subject, str):
        raise ValueError("O sujeito do token deve ser uma string não vazia")
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    if expires_delta <= timedelta(0):
        raise ValueError("O tempo de vida do token deve ser positivo")

    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + expires_delta}
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    if not isinstance(token, str) or len(token) > _MAX_TOKEN_CHARS:
        return None
    try:
        return jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except InvalidTokenError:
        return None


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credenciais_invalidas

    usuario_id = payload.get("sub")
    if (
        not isinstance(usuario_id, str)
        or not _USER_ID_PATTERN.fullmatch(usuario_id)
        or int(usuario_id) > 2**63 - 1
    ):
        raise credenciais_invalidas

    usuario = db.get(Usuario, int(usuario_id))
    if usuario is None or not usuario.ativo:
        raise credenciais_invalidas

    return usuario


def exigir_perfil(*perfis_permitidos: PerfilEnum):
    def verificador(
        usuario_atual: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if usuario_atual.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return usuario_atual

    return verificador
