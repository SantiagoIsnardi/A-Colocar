"""
Uso:
    python -m app.cli.seed_odds_the_odds_api premier_league
    python -m app.cli.seed_odds_the_odds_api la_liga

Trae cuotas de The Odds API y las cruza contra partidos programados
que ya existan en tu base (de cualquier fuente — API-Football o
football-data.org), por nombre de equipo + fecha.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.odds.odds_ingestion_service import TheOddsApiIngestionService
from app.services.odds.the_odds_api_client import SPORT_KEYS, TheOddsApiClient


async def main(competition_key: str) -> None:
    setup_logging()

    if not settings.odds_api_key:
        print("ERROR: ODDS_API_KEY no configurada en el .env")
        sys.exit(1)

    sport_key = SPORT_KEYS.get(competition_key)
    if not sport_key:
        print(f"ERROR: competición desconocida {competition_key!r}. Válidas: {sorted(SPORT_KEYS)}")
        sys.exit(1)

    client = TheOddsApiClient(api_key=settings.odds_api_key, base_url=settings.odds_api_base_url)

    try:
        async with AsyncSessionLocal() as session:
            service = TheOddsApiIngestionService(session=session, client=client)
            result = await service.ingest_odds_for_sport(sport_key=sport_key)
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.cli.seed_odds_the_odds_api <competicion>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))