
import logging

from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001  # pragma: no cover - defensivo para erros inesperados
            logger.exception(
                "Unhandled exception while handling %s %s",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Erro interno do servidor"},
            )




def add_exception_middleware(app: FastAPI) -> None:
    app.add_middleware(ExceptionMiddleware)
