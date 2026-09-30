from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from starlette.requests import Request
from starlette.responses import JSONResponse




class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensivo para erros inesperados
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": str(exc),
                },
            )




def add_exception_middleware(app: FastAPI) -> None:
    app.add_middleware(ExceptionMiddleware)