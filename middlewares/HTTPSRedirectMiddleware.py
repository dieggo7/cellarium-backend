from fastapi import FastAPI
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware


def add_https_redirect_middleware(app: FastAPI) -> None:
    app.add_middleware(HTTPSRedirectMiddleware)
