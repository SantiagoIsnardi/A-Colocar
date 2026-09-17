"""
Uso:
    python -m app.cli.sync_sofascore_statuses "Argentina Liga Profesional" 2026

Actualiza status/resultado de partidos de Sofascore ya cargados (ej: pasaron
de 'scheduled' a 'finished'), sin insertar partidos nuevos.
"""

import asyncio
import sys

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.sofascore.client import SofascoreClient
from app.services.sofascore.ingestion_service import SofascoreIngestionService


async def main(league: str, year: str) -> None:
    setup_logging()
    client = SofascoreClient()

    async with AsyncSessionLocal() as session:
        service = SofascoreIngestionService(session=session, client=client)
        result = await service.sync_match_statuses(league=league, year=year)
        print(result)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Uso: python -m app.cli.sync_sofascore_statuses "<liga>" <temporada>')
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))