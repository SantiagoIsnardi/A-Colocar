from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
    }
    