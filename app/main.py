from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config.settings import settings
from database.init_db import init_db
from middlewares.cors import add_cors_middleware
from middlewares.ExceptionMiddleware import add_exception_middleware
from middlewares.HTTPSRedirectMiddleware import add_https_redirect_middleware
from middlewares.ServerErrorMiddleware import add_server_error_middleware
from middlewares.TrustedHostMiddleware import add_trusted_host_middleware
from routes.atendimentos import router as atendimentos_router
from routes.auth import router as auth_router
from routes.categorias import router as categorias_router
from routes.dashboard import router as dashboard_router
from routes.estoque import router as estoque_router
from routes.health import router as health_router
from routes.localizacoes import router as localizacoes_router
from routes.materiais import router as materiais_router
from routes.movimentacoes import router as movimentacoes_router
from routes.movimentacoes import router_materiais as router_materiais_movimentacoes
from routes.orders import router as orders_router
from routes.projects import router as projects_router
from routes.requisicoes import router as requisicoes_router
from routes.requisicoes_itens import router as requisicoes_itens_router
from routes.setores import router as setores_router
from routes.unidades_medida import router as unidades_medida_router
from routes.usuarios import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            field = ".".join(
                str(part)
                for part in error["loc"]
                if part not in {"body", "query", "path"}
            )
            error_type = error["type"]
            if error_type == "missing":
                message = "Campo obrigatório"
            elif error_type in {"greater_than", "greater_than_equal"}:
                message = "Valor fora do limite permitido"
            elif error_type in {"int_parsing", "int_type"}:
                message = "Informe um número inteiro válido"
            elif error_type in {"decimal_parsing", "decimal_type", "float_parsing"}:
                message = "Informe um número válido"
            else:
                message = "Valor inválido"
            errors.append({"campo": field or "request", "mensagem": message})
        return JSONResponse(
            status_code=400, content={"detail": "Dados inválidos", "erros": errors}
        )

    @app.on_event("startup")
    def startup_event() -> None:
        init_db()

    add_exception_middleware(app)
    add_server_error_middleware(app)
    add_https_redirect_middleware(app)
    add_trusted_host_middleware(app)
    add_cors_middleware(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(projects_router)
    app.include_router(orders_router)
    app.include_router(dashboard_router)
    app.include_router(setores_router)
    app.include_router(materiais_router)
    app.include_router(categorias_router)
    app.include_router(localizacoes_router)
    app.include_router(estoque_router)
    app.include_router(unidades_medida_router)
    app.include_router(atendimentos_router)
    app.include_router(requisicoes_router)
    app.include_router(requisicoes_itens_router)
    app.include_router(movimentacoes_router)
    app.include_router(router_materiais_movimentacoes)

    @app.get("/")
    def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "documentation": "/docs",
            "routes": [
                "/health",
                "/auth/login",
                "/auth/me",
                "/auth/logout",
                "/auth/refresh",
                "/usuarios",
                "/setores",
                "/categorias",
                "/unidades-medida",
                "/materiais",
                "/localizacoes",
                "/estoque",
                "/requisicoes",
                "/atendimentos",
                "/movimentacoes",
                "/dashboard",
                "/projects",
                "/orders",
            ],
        }

    return app


app = create_app()
