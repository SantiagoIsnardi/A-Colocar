"""
Uso:
    python -m app.cli.seed_odds <match_id_interno>

match_id_interno es el id de la tabla matches (no el external_id de la API).
El script busca el external_id correspondiente y consulta las cuotas.
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.models.match import Match
from app.db.session import AsyncSessionLocal
from app.services.odds.odds_ingestion_service import OddsIngestionService
from app.services.sports_api.client import APIFootballClient


async def main(match_id: int) -> None:
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
            result = await session.execute(select(Match).where(Match.id == match_id))
            match = result.scalar_one_or_none()

            if not match:
                print(f"ERROR: match_id={match_id} no encontrado")
                sys.exit(1)

            service = OddsIngestionService(session=session, client=client)
            result = await service.ingest_match_odds(
                match_id=match.id,
                fixture_external_id=int(match.external_id),
            )
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.cli.seed_odds <match_id>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1])))