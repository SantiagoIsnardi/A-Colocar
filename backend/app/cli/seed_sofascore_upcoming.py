"""
Uso:
    python -m app.cli.seed_sofascore_upcoming "Argentina Liga Profesional" 2026 10
"""

import asyncio
import sys

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.sofascore.client import SofascoreClient
from app.services.sofascore.ingestion_service import SofascoreIngestionService


async def main(league: str, year: str, max_matches: int | None) -> None:
    setup_logging()

    client = SofascoreClient()

    async with AsyncSessionLocal() as session:
        service = SofascoreIngestionService(session=session, client=client)
        result = await service.ingest_upcoming_matches(
            league=league, year=year, max_matches=max_matches
        )
        print(result)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Uso: python -m app.cli.seed_sofascore_upcoming "<liga>" <año> [max_partidos]')
        sys.exit(1)
    _league = sys.argv[1]
    _year = sys.argv[2]
    _max = int(sys.argv[3]) if len(sys.argv) > 3 else None
    asyncio.run(main(_league, _year, _max))