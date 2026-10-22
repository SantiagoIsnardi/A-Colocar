"""
Scheduler interno que corre dentro del propio proceso del backend.
Alternativa gratuita a los Cron Jobs de pago de Render — las tareas
solo se ejecutan mientras el Web Service esté despierto (no duerme
solo para esto, pero si el servicio entero se duerme por inactividad,
el scheduler también se pausa hasta que algo lo despierte).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE DE JOBS EN RENDER (CLOUD) — regla arquitectural estricta
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PERMITIDO en este scheduler:
   - Sincronización de estados/resultados via football-data.org (API REST pura)
   - Ingesta incremental de partidos próximos via football-data.org
   - Calibration Engine (resolve_predictions → BrierScore + CLV)
   - Auto-generación de predicciones (Poisson + Dixon-Coles)

❌ PROHIBIDO en este scheduler (ejecutar solo desde entorno local):
   - Sofascore / SofascoreClient: requiere Chrome + Botasaurus para
     evadir Cloudflare. Render no tiene GPU ni Chrome headful disponible.
   - API-Football (ingesta de partidos): la ingesta masiva consume cuota
     de requests y se gestiona manualmente desde scripts CLI locales.
     El endpoint get_upcoming_by_league puede usarse localmente via CLI.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cronograma UTC de jobs (hora local ART = UTC-3):
  06:00 UTC (03:00 ART) — sync_statuses:            resultados de la jornada anterior
  07:00 UTC (04:00 ART) — resolve_predictions:       calibración post-resultados
  08:00 UTC (05:00 ART) — ingest_upcoming_football_data: partidos próximos (football-data.org)
  16:00 UTC (13:00 ART) — generate_missing_predictions: predicciones para partidos del día
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import logger

# Competiciones europeas cubiertas por football-data.org (free tier).
# Se sincronizan en secuencia para respetar el rate limit de 10 req/min.
_FOOTBALL_DATA_COMPETITIONS = ["PL", "PD", "BL1", "SA", "CL", "BSA"]

scheduler = AsyncIOScheduler()


# ─────────────────────────────────────────────────────────────────────────────
# JOB 1 — Sync de estados y resultados (football-data.org)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_sync_statuses() -> None:
    """
    Actualiza status (scheduled → finished) y marcadores de todos los partidos
    ya existentes en la DB para las 6 competiciones de football-data.org.
    Corre a las 06:00 UTC para capturar resultados de la jornada anterior.
    """
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.services.football_data.client import FootballDataClient
    from app.services.football_data.ingestion_service import FootballDataIngestionService

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
            total_updated = 0
            for code in _FOOTBALL_DATA_COMPETITIONS:
                try:
                    result = await service.sync_match_statuses(competition_code=code)
                    total_updated += result.get("matches_updated", 0)
                except Exception as exc:
                    # Un fallo en una competición no debe interrumpir las restantes
                    logger.error("Scheduler | sync_statuses error en {}: {}", code, exc)
            logger.info(
                "Scheduler | sync_statuses completado | competiciones={} | total_actualizados={}",
                len(_FOOTBALL_DATA_COMPETITIONS), total_updated,
            )
    except Exception as exc:
        logger.error("Scheduler | error fatal en sync_statuses: {}", exc)
    finally:
        await client.close()


# ─────────────────────────────────────────────────────────────────────────────
# JOB 2 — Calibration Engine (resolve_predictions)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_resolve_predictions() -> None:
    """
    Resuelve predicciones pendientes contra resultados reales:
    calcula BrierScore y CLV para cada predicción con partido ya finalizado.
    Corre a las 07:00 UTC, después del sync de estados.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.calibration.calibration_engine import CalibrationEngine

    try:
        async with AsyncSessionLocal() as session:
            engine = CalibrationEngine(session)
            result = await engine.resolve_all_pending()
            logger.info("Scheduler | resolve_predictions completado: {}", result)
    except Exception as exc:
        logger.error("Scheduler | error en resolve_predictions: {}", exc)


# ─────────────────────────────────────────────────────────────────────────────
# JOB 3 — Ingesta incremental de partidos próximos (football-data.org)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_ingest_upcoming_football_data() -> None:
    """
    Ingesta incremental de partidos con status SCHEDULED para todas las
    competiciones de football-data.org. Usa UniqueConstraint para inserción
    idempotente: partidos ya existentes se cuentan como 'omitidos' sin error.
    Corre a las 08:00 UTC, después de la calibración.

    NOTA: Esta tarea usa football-data.org (API REST pura). No involucra
    Sofascore ni API-Football — ambas fuentes son de ejecución LOCAL ONLY.
    """
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.services.football_data.client import FootballDataClient
    from app.services.football_data.ingestion_service import FootballDataIngestionService

    if not settings.football_data_api_key:
        logger.warning(
            "Scheduler: FOOTBALL_DATA_API_KEY no configurada, se salta ingest_upcoming"
        )
        return

    client = FootballDataClient(
        api_key=settings.football_data_api_key,
        base_url=settings.football_data_base_url,
    )
    try:
        async with AsyncSessionLocal() as session:
            service = FootballDataIngestionService(session=session, client=client)
            total_created = 0
            total_skipped = 0
            for code in _FOOTBALL_DATA_COMPETITIONS:
                try:
                    result = await service.ingest_competition_matches(
                        competition_code=code,
                        status="SCHEDULED",
                    )
                    total_created += result.get("matches_created", 0)
                    total_skipped += result.get("matches_skipped", 0)
                except Exception as exc:
                    logger.error(
                        "Scheduler | ingest_upcoming error en {}: {}", code, exc
                    )
            logger.info(
                "Scheduler | ingest_upcoming_football_data completado | "
                "competiciones={} | creados={} | omitidos={}",
                len(_FOOTBALL_DATA_COMPETITIONS), total_created, total_skipped,
            )
    except Exception as exc:
        logger.error("Scheduler | error fatal en ingest_upcoming_football_data: {}", exc)
    finally:
        await client.close()


# ─────────────────────────────────────────────────────────────────────────────
# JOB 4 — Auto-generación de predicciones faltantes
# ─────────────────────────────────────────────────────────────────────────────

async def _run_generate_missing_predictions() -> None:
    """
    Auto-genera predicciones (mercado 'goals', líneas 0.5–4.5) para todos
    los partidos con status 'scheduled' que todavía no tengan predicción.
    Corre a las 16:00 UTC (13:00 ART), después de que el operador haya
    corrido localmente el scraper de Sofascore y la ingesta de API-Football
    para cargar los partidos del día/semana.

    NOTA: Este job solo ejecuta modelos matemáticos internos (Poisson +
    Dixon-Coles + ContextEngine). No llama a ninguna API externa.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.prediction.auto_predictor import AutoPredictor

    try:
        predictor = AutoPredictor(AsyncSessionLocal)
        result = await predictor.generate_missing()
        logger.info("Scheduler | generate_missing_predictions completado: {}", result)
    except Exception as exc:
        logger.error("Scheduler | error en generate_missing_predictions: {}", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Arranque y parada
# ─────────────────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Registra los jobs y arranca el scheduler. Se llama una vez al iniciar la app."""
    scheduler.add_job(
        _run_sync_statuses,
        trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
        id="sync_football_data_statuses",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_resolve_predictions,
        trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
        id="resolve_predictions",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_ingest_upcoming_football_data,
        trigger=CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="ingest_upcoming_football_data",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_generate_missing_predictions,
        trigger=CronTrigger(hour=16, minute=0, timezone="UTC"),
        id="generate_missing_predictions",
        replace_existing=True,
    )
    scheduler.start()
    jobs = scheduler.get_jobs()
    logger.info("Scheduler iniciado | jobs={}", [j.id for j in jobs])


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
