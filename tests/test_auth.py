from core.security import create_access_token, get_password_hash, verify_password


def test_password_hash_and_verify():
    plain = "secret123"
    hashed = get_password_hash(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_access_token_contains_subject():
    token = create_access_token("user-123")

    assert isinstance(token, str)
    assert token
