
from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001  # pragma: no cover - defensivo para erros inesperados
            return JSONResponse(
                status_code=500,
                content={"detail": "Erro interno do servidor"},
            )




def add_exception_middleware(app: FastAPI) -> None:
    app.add_middleware(ExceptionMiddleware)