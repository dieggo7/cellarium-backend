from fastapi import FastAPI

import app
from config.settings import settings
from database.init_db import init_db
from middlewares.cors import add_cors_middleware
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.health import router as health_router
from routes.orders import router as orders_router
from routes.projects import router as projects_router
from routes.users import router as users_router
from routes.setores import router as setores_router
from routes.materiais import router as materiais_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    @app.on_event("startup")
    def startup_event() -> None:
        init_db()

    add_cors_middleware(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(projects_router)
    app.include_router(orders_router)
    app.include_router(dashboard_router)
    app.include_router(setores_router)
    app.include_router(materiais_router)

    @app.get("/")
    def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "routes": [
                "/auth/login",
                "/auth/register",
                "/auth/me",
                "/users",
                "/projects",
                "/orders",
                "/dashboard",
            ],
        }

    return app


app = create_app()
