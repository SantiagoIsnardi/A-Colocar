"""
Carga histórica incremental de API-Football, respetando un presupuesto
diario fijo. Reanudable: cada corrida continúa desde el equipo/temporada
donde quedó la vez anterior, usando un cursor guardado en disco.

Uso diario (correr una vez por día, hasta agotar las 2 temporadas):
    python -m app.cli.seed_incremental_api_football

Cada corrida consume como máximo DAILY_REQUEST_BUDGET requests, dejando
margen sobre el límite real de 100/día por si el mapper necesita crear
equipos nuevos en el camino (cada creación de equipo no gasta request
extra, pero es buena práctica no ir al límite exacto).
"""

import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.rate_budget import RateBudget
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService

DAILY_REQUEST_BUDGET = 90  # margen de seguridad sobre el límite real de 100
CURSOR_FILE = Path(__file__).parent.parent.parent / ".seed_cursor_api_football.json"

# Equipos objetivo para cobertura sudamericana — ampliar según necesidad
TARGET_TEAMS = [
    "River Plate", "Boca Juniors", "Racing Club", "Independiente",
    "San Lorenzo", "Velez Sarsfield", "Estudiantes", "Talleres",
]
SEASONS = [2023, 2024]  # las 2 temporadas disponibles en el plan free


def _load_cursor() -> dict:
    if not CURSOR_FILE.exists():
        return {"team_index": 0, "season_index": 0}
    return json.loads(CURSOR_FILE.read_text())


def _save_cursor(cursor: dict) -> None:
    CURSOR_FILE.write_text(json.dumps(cursor, indent=2))


async def main() -> None:
    setup_logging()

    if not settings.api_football_key:
        print("ERROR: API_FOOTBALL_KEY no configurada en el .env")
        return

    budget = RateBudget(provider="api_football", daily_limit=DAILY_REQUEST_BUDGET)
    remaining = budget.remaining_today()

    if remaining <= 0:
        print(f"Presupuesto diario agotado ({DAILY_REQUEST_BUDGET} requests). Volvé a correr mañana.")
        return

    cursor = _load_cursor()
    client = APIFootballClient(api_key=settings.api_football_key, base_url=settings.api_football_base_url)

    requests_used = 0
    results = []

    try:
        async with AsyncSessionLocal() as session:
            service = IngestionService(session=session, client=client)

            while requests_used < remaining and cursor["team_index"] < len(TARGET_TEAMS):
                team_name = TARGET_TEAMS[cursor["team_index"]]
                season = SEASONS[cursor["season_index"]]

                try:
                    result = await service.ingest_team_fixtures(
                        team_name=team_name, season=season, last_n=20
                    )
                    requests_used += 2  # aprox: 1 búsqueda de equipo + 1 fixtures
                    results.append({"team": team_name, "season": season, **result})
                    logger.info(
                        "Cargado {} temporada {} | creados={}",
                        team_name, season, result.get("fixtures_created", 0),
                    )
                except Exception as exc:
                    logger.error("Error cargando {} temporada {}: {}", team_name, season, exc)
                    results.append({"team": team_name, "season": season, "error": str(exc)})
                    requests_used += 1

                # Avanzar el cursor: primero todas las temporadas de un equipo, después el siguiente
                cursor["season_index"] += 1
                if cursor["season_index"] >= len(SEASONS):
                    cursor["season_index"] = 0
                    cursor["team_index"] += 1

                _save_cursor(cursor)

            budget.record_usage(requests_used)

    finally:
        await client.close()

    if cursor["team_index"] >= len(TARGET_TEAMS):
        print("✅ Carga completa — todos los equipos y temporadas objetivo fueron procesados.")
    else:
        next_team = TARGET_TEAMS[cursor["team_index"]]
        print(f"Progreso guardado. Próxima corrida continúa desde: {next_team}")

    print(f"Requests usados hoy: {requests_used} | Presupuesto diario: {DAILY_REQUEST_BUDGET}")
    for r in results:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())