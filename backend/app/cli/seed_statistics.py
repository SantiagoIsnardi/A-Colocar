"""
Uso:
    python -m app.cli.seed_statistics 10
    (el número es el límite de partidos a procesar, default 10)
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService


async def main(limit: int) -> None:
    setup_logging()

    if not settings.api_football_key:
        print("ERROR: API_FOOTBALL_KEY no configurada en el .env")
        sys.exit(1)

    client = APIFootballClient(
        api_key=settings.api_football_key,
        base_url=settings.api_football_base_url,
    )

    try:
        async with AsyncSessionLocal() as session:
            service = IngestionService(session=session, client=client)
            result = await service.ingest_match_statistics(limit=limit)
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    _limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(main(_limit))