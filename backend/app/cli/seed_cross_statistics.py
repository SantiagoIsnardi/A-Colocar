"""
Uso:
    python -m app.cli.seed_cross_statistics 10

Completa estadísticas detalladas para partidos de football-data.org
(ya finalizados, sin stats todavía) cruzando contra API-Football.
Cada partido consume 2-3 requests de API-Football (búsqueda de equipos +
fixtures + statistics), así que el límite por corrida es conservador.
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.models.match import Match, MatchStatus
from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService


async def main(limit: int) -> None:
    setup_logging()

    print(
        "\n⚠️  AVISO: este cruce fue descartado tras pruebas reales (Sprint 10).\n"
        "   El matcheo por nombre entre football_data y api_football no es\n"
        "   confiable y consume cuota de requests rápidamente sin garantía\n"
        "   de éxito. Ver docstring de ingest_statistics_for_football_data_match.\n"
        "   Los mercados corners/yellow_cards/fouls/shots solo están disponibles\n"
        "   para partidos ingeridos directamente vía API-Football.\n"
    )

    if not settings.api_football_key:
        print("ERROR: API_FOOTBALL_KEY no configurada en el .env")
        sys.exit(1)

    client = APIFootballClient(
        api_key=settings.api_football_key,
        base_url=settings.api_football_base_url,
    )

    try:
        async with AsyncSessionLocal() as session:
            stats_repo = StatisticsRepository(session)
            matches_with_stats = await stats_repo.matches_with_statistics()

            result = await session.execute(
                select(Match).where(
                    Match.source == "football_data",
                    Match.status == MatchStatus.finished,
                )
            )
            all_matches = result.scalars().all()
            pending = [m for m in all_matches if m.id not in matches_with_stats][:limit]

            if not pending:
                print("No hay partidos pendientes de cruce de estadísticas.")
                return

            service = IngestionService(session=session, client=client)
            results = []

            for match in pending:
                result = await service.ingest_statistics_for_football_data_match(match.id)
                results.append(result)
                print(result)

            success_count = sum(1 for r in results if r.get("statistics_created", 0) > 0)
            print(f"\nResumen: {success_count}/{len(pending)} partidos con estadísticas cruzadas exitosamente")

    finally:
        await client.close()


if __name__ == "__main__":
    _limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(main(_limit))