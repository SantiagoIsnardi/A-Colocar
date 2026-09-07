"""
Traduce la jerarquía de excepciones propia (app.core.exceptions) en
respuestas HTTP consistentes, y captura cualquier excepción no prevista
sin filtrar detalles internos al cliente.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logging import logger


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "AppException | path={} | status={} | message={}",
            request.url.path, exc.status_code, exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Excepción no manejada | path={} | tipo={} | error={}",
            request.url.path, type(exc).__name__, str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"},
        )