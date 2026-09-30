from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings


def add_trusted_host_middleware(app: FastAPI) -> None:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
