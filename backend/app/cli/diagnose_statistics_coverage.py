"""
Diagnóstico de solo-lectura: recorre TODOS los partidos finalizados de
api_football sin estadísticas y clasifica cada uno según el resultado
real de /fixtures/statistics, sin escribir nada en la base.

Uso:
    python -m app.cli.diagnose_statistics_coverage

Categorías:
    - ok: la API devuelve estadísticas de los equipos correctos
    - sin_datos: la API responde vacío (cobertura real limitada)
    - equipo_desconocido: la API devuelve datos de equipos que no
      coinciden con los guardados — fixture ID inconsistente del lado
      de la API, no es corregible desde nuestro código
    - error: fallo de red/parseo inesperado, incluso tras reintento
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.models.match import Match, MatchStatus
from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.team_repository import TeamRepository
from app.db.session import AsyncSessionLocal
from app.services.sports_api.client import APIFootballClient

DELAY_SECONDS = 3.0  # pausa entre requests — 1.5s resultó insuficiente, sigue chocando con 429
RATE_LIMIT_COOLDOWN = 15.0  # pausa extra cuando se detecta un 429, antes de reintentar una vez


def _classify(team_stats_list: list[dict], home_ext_id: str, away_ext_id: str) -> str:
    if not team_stats_list:
        return "sin_datos"
    api_team_ids = {str(ts["team"]["id"]) for ts in team_stats_list}
    expected_ids = {home_ext_id, away_ext_id}
    return "ok" if (api_team_ids & expected_ids) else "equipo_desconocido"


async def main() -> None:
    setup_logging()

    if not settings.api_football_key:
        print("ERROR: API_FOOTBALL_KEY no configurada en el .env")
        return

    client = APIFootballClient(api_key=settings.api_football_key, base_url=settings.api_football_base_url)

    categories: dict[str, list[str]] = {
        "ok": [],
        "sin_datos": [],
        "equipo_desconocido": [],
        "error": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            team_repo = TeamRepository(session)
            stats_repo = StatisticsRepository(session)

            matches_with_stats = await stats_repo.matches_with_statistics()

            result = await session.execute(
                select(Match).where(
                    Match.source == "api_football",
                    Match.status == MatchStatus.finished,
                )
            )
            all_matches = [m for m in result.scalars().all() if m.id not in matches_with_stats]

            print(f"Diagnosticando {len(all_matches)} partidos sin estadísticas (source=api_football)...\n")

            for i, match in enumerate(all_matches):
                if i > 0:
                    await asyncio.sleep(DELAY_SECONDS)

                try:
                    home_team = await team_repo.get_by_id(match.home_team_id)
                    away_team = await team_repo.get_by_id(match.away_team_id)

                    if not home_team or not away_team:
                        categories["error"].append(match.external_id)
                        continue

                    stats_data = await client.get_fixture_statistics(int(match.external_id))
                    team_stats_list = stats_data.get("response", [])
                    category = _classify(team_stats_list, home_team.external_id, away_team.external_id)
                    categories[category].append(match.external_id)

                except Exception as exc:
                    if "límite de requests" in str(exc).lower():
                        logger.warning(
                            "Rate limit en fixture {} — pausa de {}s y reintento único",
                            match.external_id, RATE_LIMIT_COOLDOWN,
                        )
                        await asyncio.sleep(RATE_LIMIT_COOLDOWN)
                        try:
                            stats_data = await client.get_fixture_statistics(int(match.external_id))
                            team_stats_list = stats_data.get("response", [])
                            category = _classify(team_stats_list, home_team.external_id, away_team.external_id)
                            categories[category].append(match.external_id)
                        except Exception as retry_exc:
                            logger.error("Fallo también en el reintento de {}: {}", match.external_id, retry_exc)
                            categories["error"].append(match.external_id)
                    else:
                        logger.error("Error diagnosticando fixture {}: {}", match.external_id, exc)
                        categories["error"].append(match.external_id)

                print(f"  [{i + 1}/{len(all_matches)}] fixture={match.external_id} -> procesado")

    finally:
        await client.close()

    total = sum(len(v) for v in categories.values())
    print("\n" + "=" * 50)
    print("RESULTADO DEL DIAGNÓSTICO")
    print("=" * 50)
    for category, ids in categories.items():
        pct = (len(ids) / total * 100) if total else 0
        print(f"  {category:20s}: {len(ids):3d} partidos ({pct:.1f}%)")
    print(f"  {'TOTAL':20s}: {total:3d} partidos")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())