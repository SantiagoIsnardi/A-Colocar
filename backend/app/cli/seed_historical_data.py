"""
Uso:
    python -m app.cli.seed_historical_data "Barcelona" 2024
    python -m app.cli.seed_historical_data "Real Madrid" 2024 30
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService


async def main(team_name: str, season: int, last_n: int) -> None:
    setup_logging()

    if not settings.api_football_key:
        print("ERROR: API_FOOTBALL_KEY no está configurada en el .env")
        sys.exit(1)

    client = APIFootballClient(
        api_key=settings.api_football_key,
        base_url=settings.api_football_base_url,
    )

    try:
        async with AsyncSessionLocal() as session:
            service = IngestionService(session=session, client=client)
            result = await service.ingest_team_fixtures(
                team_name=team_name,
                season=season,
                last_n=last_n,
            )
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    _team = sys.argv[1] if len(sys.argv) > 1 else "Barcelona"
    _season = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
    _last = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    asyncio.run(main(_team, _season, _last))