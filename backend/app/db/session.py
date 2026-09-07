"""
Configura el engine asíncrono de SQLAlchemy y expone la dependencia
get_db(), usada por FastAPI para inyectar una sesión de base de datos
por request.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,    # imprime las queries SQL solo en modo debug
    pool_pre_ping=True,     # valida la conexión antes de usarla, evita conexiones muertas
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI. Entrega una sesión por request
    y la cierra automáticamente al finalizar, incluso si hay errores.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()