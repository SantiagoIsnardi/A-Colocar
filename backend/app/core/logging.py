"""
Configuración de logging estructurado con loguru.
En desarrollo: logs coloreados y legibles en consola.
En producción: logs en formato JSON para ingestión por herramientas externas.
"""

import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """
    Reemplaza el sink por defecto de loguru y configura el formato
    según el entorno de ejecución.
    """
    logger.remove()  # elimina el handler por defecto de loguru

    if settings.is_production:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            serialize=True,  # logs en JSON
            backtrace=False,
            diagnose=False,
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
                "- <level>{message}</level>"
            ),
            backtrace=True,
            diagnose=True,
        )

    logger.info(
        "Logging configurado | entorno={} | nivel={}",
        settings.environment,
        settings.log_level,
    )


__all__ = ["logger", "setup_logging"]