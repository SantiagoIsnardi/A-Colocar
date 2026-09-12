"""
Scheduler interno que corre dentro del propio proceso del backend.
Alternativa gratuita a los Cron Jobs de pago de Render — las tareas
solo se ejecutan mientras el Web Service esté despierto (no duerme
solo para esto, pero si el servicio entero se duerme por inactividad,
el scheduler también se pausa hasta que algo lo despierte).
"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import logger

scheduler = AsyncIOScheduler()


async def _run_sync_statuses() -> None:
    """Sincroniza estados de partidos de football-data.org (scheduled -> finished)."""
    from app.db.session import AsyncSessionLocal
    from app.services.football_data.client import FootballDataClient
    from app.services.football_data.ingestion_service import FootballDataIngestionService
    from app.core.config import settings

    if not settings.football_data_api_key:
        logger.warning("Scheduler: FOOTBALL_DATA_API_KEY no configurada, se salta sync_statuses")
        return

    client = FootballDataClient(
        api_key=settings.football_data_api_key,
        base_url=settings.football_data_base_url,
    )
    try:
        async with AsyncSessionLocal() as session:
            service = FootballDataIngestionService(session=session, client=client)
            result = await service.sync_match_statuses(competition_code="PL")
            logger.info("Scheduler | sync_statuses completado: {}", result)
    except Exception as exc:
        logger.error("Scheduler | error en sync_statuses: {}", exc)
    finally:
        await client.close()


async def _run_resolve_predictions() -> None:
    """Resuelve predicciones pendientes contra resultados reales (Calibration Engine)."""
    from app.db.session import AsyncSessionLocal
    from app.services.calibration.calibration_engine import CalibrationEngine

    try:
        async with AsyncSessionLocal() as session:
            engine = CalibrationEngine(session)
            result = await engine.resolve_all_pending()
            logger.info("Scheduler | resolve_predictions completado: {}", result)
    except Exception as exc:
        logger.error("Scheduler | error en resolve_predictions: {}", exc)


def start_scheduler() -> None:
    """Registra los jobs y arranca el scheduler. Se llama una vez al iniciar la app."""
    scheduler.add_job(
        _run_sync_statuses,
        trigger=CronTrigger(hour=6, minute=0),  # todos los días 6:00 UTC
        id="sync_football_data_statuses",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_resolve_predictions,
        trigger=CronTrigger(hour=7, minute=0),  # después del sync, 7:00 UTC
        id="resolve_predictions",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado con {} jobs programados", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")