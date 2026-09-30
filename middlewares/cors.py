from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings


def build_allowed_origins() -> list[str]:

    origins = [origin.strip() for origin in settings.allowed_origins if origin and origin.strip()]
    frontend_origin = settings.frontend_url.strip()

    if frontend_origin and frontend_origin not in origins:
        origins.append(frontend_origin)

    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")

    if "http://127.0.0.1:3000" not in origins:
        origins.append("http://127.0.0.1:3000")

    return origins


def add_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=build_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
        expose_headers=["Authorization"],
        max_age=600,
    )
