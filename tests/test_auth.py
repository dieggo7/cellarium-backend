import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from config.settings import Settings, settings
from core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from models.usuario import PerfilEnum
from routes.auth import autenticar_usuario
from routes.usuarios import (
    UsuarioCreateRequest,
    UsuarioUpdateRequest,
    create_usuario,
    update_usuario,
)


def test_password_hash_and_verify():
    plain = "secret123"
    hashed = get_password_hash(plain)

    assert hashed != plain
    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_is_not_truncated_at_72_bytes():
    plain = "á" * 40
    hashed = get_password_hash(plain)

    assert verify_password(plain, hashed)
    assert not verify_password("á" * 36 + "outra", hashed)


def test_legacy_bcrypt_hash_and_invalid_hash():
    legacy = bcrypt.hashpw(b"old-password", bcrypt.gensalt(rounds=4)).decode("ascii")

    assert verify_password("old-password", legacy)
    assert not verify_password("old-password" + "x" * 80, legacy)
    assert not verify_password("old-password", "$2b$invalid")
    assert not verify_password("old-password", "unsupported-format")


def test_successful_legacy_login_rehashes_password():
    old_hash = bcrypt.hashpw(b"old-password", bcrypt.gensalt(rounds=4)).decode("ascii")
    usuario = SimpleNamespace(ativo=True, senha_hash=old_hash)
    db = Mock()
    db.scalar.return_value = usuario

    assert autenticar_usuario(db, "old-user", "old-password") is usuario
    assert usuario.senha_hash.startswith("$argon2id$")
    assert verify_password("old-password", usuario.senha_hash)
    db.commit.assert_called_once()


def test_password_size_limit():
    with pytest.raises(ValueError):
        get_password_hash("a" * 1025)
    assert not verify_password("a" * 1025, get_password_hash("short"))


def test_create_access_token_contains_subject():
    token = create_access_token("user-123")

    assert isinstance(token, str)
    assert token
    assert decode_access_token(token)["sub"] == "user-123"


def test_decode_rejects_expired_missing_claims_and_wrong_algorithm():
    key = settings.secret_key.get_secret_value()
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": "1", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        key,
        algorithm="HS256",
    )
    missing_exp = jwt.encode({"sub": "1", "iat": now}, key, algorithm="HS256")
    wrong_algorithm = jwt.encode(
        {"sub": "1", "iat": now, "exp": now + timedelta(hours=1)},
        key,
        algorithm="HS384",
    )

    assert decode_access_token(expired) is None
    assert decode_access_token(missing_exp) is None
    assert decode_access_token(wrong_algorithm) is None
    assert decode_access_token("x" * 4097) is None


def test_get_current_user_rejects_invalid_subject_and_inactive_user():
    db = Mock()
    with pytest.raises(HTTPException) as error:
        get_current_user(create_access_token("not-an-id"), db)
    assert error.value.status_code == 401
    db.get.assert_not_called()

    db.get.return_value = SimpleNamespace(ativo=False)
    with pytest.raises(HTTPException) as error:
        get_current_user(create_access_token("1"), db)
    assert error.value.status_code == 401


def test_token_expiration_must_be_positive():
    with pytest.raises(ValueError):
        create_access_token("1", timedelta(0))


def test_user_creation_requires_authentication():
    response = TestClient(app, base_url="http://localhost").post(
        "/usuarios",
        json={"nome": "X", "login": "x", "senha": "secret", "perfil": "ADMIN"},
    )
    assert response.status_code == 401


def test_user_creation_rejects_oversized_password():
    with pytest.raises(ValidationError):
        UsuarioCreateRequest(nome="X", login="x", senha="á" * 513)


def test_manager_cannot_assign_admin_role():
    db = Mock()
    manager = SimpleNamespace(perfil=PerfilEnum.gestor)
    payload = UsuarioCreateRequest(
        nome="X", login="x", senha="secret", perfil=PerfilEnum.admin
    )

    with pytest.raises(HTTPException) as error:
        create_usuario(payload, db, manager)
    assert error.value.status_code == 403
    db.add.assert_not_called()

    db.get.return_value = SimpleNamespace(perfil=PerfilEnum.solicitante)
    with pytest.raises(HTTPException) as error:
        update_usuario(1, UsuarioUpdateRequest(perfil=PerfilEnum.admin), db, manager)
    assert error.value.status_code == 403

    db.get.return_value = SimpleNamespace(perfil=PerfilEnum.admin)
    with pytest.raises(HTTPException) as error:
        update_usuario(1, UsuarioUpdateRequest(nome="X"), db, manager)
    assert error.value.status_code == 403
    db.commit.assert_not_called()


def test_placeholder_signing_key_is_rejected():
    with pytest.raises(ValidationError):
        Settings(secret_key="change-me-" + "x" * 32)


def test_database_credentials_are_masked_in_settings():
    credential = secrets.token_hex(16)
    configured = Settings(
        database_url=f"mysql+pymysql://user:{credential}@localhost/database"
    )
    assert credential not in repr(configured)
    with pytest.raises(ValidationError):
        Settings(database_url="")
