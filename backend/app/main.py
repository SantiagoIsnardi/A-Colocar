from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import logger, setup_logging
from app.db.session import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("Arrancando {} | entorno={}", settings.app_name, settings.environment)

    from app.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    stop_scheduler()
    logger.info("Apagando {}", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

register_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Endpoint ultraliviano para keepalive de Render Free Tier.
    Devuelve status + timestamp sin tocar la base de datos.
    Usar con servicios de monitoreo externos (ping cada ≤14 min).
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/db", tags=["health"])
async def health_check_db() -> dict:
    """
    Diagnóstico completo: verifica conectividad con la base de datos.
    No usar para keepalive — tiene latencia de red a Neon.
    """
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Fallo de conexión a la base de datos: {}", exc)
        db_status = "unavailable"

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
