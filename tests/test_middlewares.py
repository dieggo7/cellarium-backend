from app.main import app


def test_app_registers_security_middlewares():
    middleware_names = {middleware.cls.__name__ for middleware in app.user_middleware}

    assert "CORSMiddleware" in middleware_names
    assert "TrustedHostMiddleware" in middleware_names
    assert "HTTPSRedirectMiddleware" in middleware_names
