from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.settings import settings
from database.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_password_hash(senha_plana: str) -> str:
    senha_bytes = senha_plana.encode("utf-8")[:72]
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            senha_plana.encode("utf-8")[:72],
            senha_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)

    expira = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expira}

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.InvalidTokenError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from models.usuario import Usuario  # import tardio, evita import circular

    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credenciais_invalidas

    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise credenciais_invalidas

    usuario = db.get(Usuario, int(usuario_id))
    if usuario is None or not usuario.ativo:
        raise credenciais_invalidas

    return usuario


def exigir_perfil(*perfis_permitidos):
    def verificador(usuario_atual=Depends(get_current_user)):
        if usuario_atual.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return usuario_atual
    return verificador