"""
Uso:
    python -m app.cli.seed_football_data PL SCHEDULED
    python -m app.cli.seed_football_data PL FINISHED 2025

Códigos válidos: PL, PD, BL1, SA, CL, BSA.
Status opcional: SCHEDULED, FINISHED (sin status trae todo).
Season opcional: año de inicio de temporada (2025 = temporada 2025/26).
Sin season, trae la temporada actual.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.football_data.client import FootballDataClient
from app.services.football_data.ingestion_service import FootballDataIngestionService


async def main(competition_code: str, status: str | None, season: int | None) -> None:
    setup_logging()

    if not settings.football_data_api_key:
        print("ERROR: FOOTBALL_DATA_API_KEY no configurada en el .env")
        sys.exit(1)

    client = FootballDataClient(
        api_key=settings.football_data_api_key,
        base_url=settings.football_data_base_url,
    )

    try:
        async with AsyncSessionLocal() as session:
            service = FootballDataIngestionService(session=session, client=client)
            result = await service.ingest_competition_matches(
                competition_code=competition_code,
                status=status,
                season=season,
            )
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.cli.seed_football_data <CODIGO> [STATUS] [SEASON]")
        sys.exit(1)
    _code = sys.argv[1]
    _status = sys.argv[2] if len(sys.argv) > 2 else None
    _season = int(sys.argv[3]) if len(sys.argv) > 3 else None
    asyncio.run(main(_code, _status, _season))