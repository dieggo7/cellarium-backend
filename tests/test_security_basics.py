from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_routes_require_authentication():
    assert client.get("/projects").status_code == 401
    assert client.get("/orders").status_code == 401
    assert client.get("/dashboard").status_code == 401


def test_security_headers_are_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "content-security-policy" in response.headers


def test_legacy_users_module_still_imports():
    from routes.users import UsuarioCreateRequest

    assert UsuarioCreateRequest is not None
