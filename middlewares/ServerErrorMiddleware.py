from fastapi import FastAPI
from starlette.middleware.errors import ServerErrorMiddleware
import time


from config.settings import settings




def add_server_error_middleware(app: FastAPI) -> None:
    app.add_middleware(
        ServerErrorMiddleware,
        debug=settings.debug,
    )