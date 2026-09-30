from fastapi import FastAPI
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from config.settings import settings


def add_https_redirect_middleware(app: FastAPI) -> None:
    if settings.force_https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware)
