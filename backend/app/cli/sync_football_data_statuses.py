"""
Uso:
    python -m app.cli.sync_football_data_statuses PL

Actualiza status/resultado de partidos ya cargados, sin insertar nuevos.
Necesario para reflejar partidos que pasaron de 'scheduled' a 'finished'.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.football_data.client import FootballDataClient
from app.services.football_data.ingestion_service import FootballDataIngestionService


async def main(competition_code: str) -> None:
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
            result = await service.sync_match_statuses(competition_code=competition_code)
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.cli.sync_football_data_statuses <CODIGO>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))