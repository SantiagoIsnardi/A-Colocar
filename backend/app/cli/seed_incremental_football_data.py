"""
Carga histórica incremental de football-data.org, respetando el límite
de 10 requests/minuto pausando entre llamadas. A diferencia de
API-Football (límite diario), acá el límite es por minuto, así que en
una sola corrida se puede cubrir bastante más terreno, simplemente
espaciando las requests.

Uso:
    python -m app.cli.seed_incremental_football_data
"""

import asyncio

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import AsyncSessionLocal
from app.services.football_data.client import COMPETITION_CODES, FootballDataClient
from app.services.football_data.ingestion_service import FootballDataIngestionService

SECONDS_BETWEEN_REQUESTS = 7  # 60s / 9 req margen de seguridad ≈ 6.6s, redondeado a 7


async def main() -> None:
    setup_logging()

    if not settings.football_data_api_key:
        print("ERROR: FOOTBALL_DATA_API_KEY no configurada en el .env")
        return

    client = FootballDataClient(
        api_key=settings.football_data_api_key,
        base_url=settings.football_data_base_url,
    )

    results = []

    try:
        async with AsyncSessionLocal() as session:
            service = FootballDataIngestionService(session=session, client=client)

            competitions = list(COMPETITION_CODES.items())
            for i, (name, code) in enumerate(competitions):
                try:
                    result = await service.ingest_competition_matches(
                        competition_code=code, status="FINISHED"
                    )
                    results.append({"competition": name, **result})
                    logger.info(
                        "Cargada {} | creados={} | omitidos={}",
                        name, result.get("matches_created", 0), result.get("matches_skipped", 0),
                    )
                except Exception as exc:
                    logger.error("Error cargando {}: {}", name, exc)
                    results.append({"competition": name, "error": str(exc)})

                if i < len(competitions) - 1:
                    await asyncio.sleep(SECONDS_BETWEEN_REQUESTS)

    finally:
        await client.close()

    print("✅ Corrida completa — todas las 6 competiciones europeas procesadas.")
    for r in results:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())