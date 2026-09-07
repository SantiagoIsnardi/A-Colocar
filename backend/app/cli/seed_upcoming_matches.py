"""
Uso:
    python -m app.cli.seed_upcoming_matches "Barcelona" 5

Ingiere próximos partidos programados (aún no jugados) de un equipo.
Necesario porque las cuotas de mercado solo existen para partidos
que todavía no se disputaron.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService


async def main(team_name: str, next_n: int) -> None:
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
            result = await service.ingest_upcoming_fixtures(team_name=team_name, next_n=next_n)
            print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    _team = sys.argv[1] if len(sys.argv) > 1 else "Barcelona"
    _next = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    asyncio.run(main(_team, _next))