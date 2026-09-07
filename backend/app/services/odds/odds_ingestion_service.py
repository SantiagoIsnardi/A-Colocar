from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.match import Match
from app.db.models.odds import Odds
from app.db.models.team import Team
from app.db.repositories.odds_repository import OddsRepository
from app.services.odds.odds_api_client import OddsApiMapper
from app.services.odds.the_odds_api_client import TheOddsApiClient
from app.services.odds.the_odds_api_mapper import TheOddsApiMapper
from app.services.sports_api.client import APIFootballClient


class OddsIngestionService:
    """
    Soporta dos proveedores de cuotas: API-Football (legacy, cobertura
    limitada en el plan gratuito) y The Odds API (recomendado — proveedor
    dedicado, sin restricción de temporada).
    """

    def __init__(self, session: AsyncSession, client: APIFootballClient | None = None) -> None:
        self.session = session
        self.client = client
        self.odds_repo = OddsRepository(session)
        self.mapper = OddsApiMapper()

    async def ingest_match_odds(self, match_id: int, fixture_external_id: int) -> dict:
        """Vía API-Football — se mantiene por compatibilidad, cobertura limitada."""
        if not self.client:
            return {"match_id": match_id, "odds_created": 0, "reason": "Cliente API-Football no provisto"}

        odds_response = await self.client.get_fixture_odds(fixture_external_id)
        rows = self.mapper.extract_odds_rows(odds_response)

        if not rows:
            logger.warning("Sin cuotas (API-Football) para fixture {} (match_id={})", fixture_external_id, match_id)
            return {"match_id": match_id, "odds_created": 0, "reason": "Sin datos de cuotas en la API"}

        created = 0
        for row in rows:
            odds = Odds(match_id=match_id, is_closing=False, **row)
            await self.odds_repo.create(odds)
            created += 1

        await self.session.commit()
        logger.info("Cuotas ingeridas (API-Football) | match_id={} | filas={}", match_id, created)
        return {"match_id": match_id, "odds_created": created}


class TheOddsApiIngestionService:
    """Ingesta de cuotas vía The Odds API, con resolución de partido por nombre + fecha."""

    def __init__(self, session: AsyncSession, client: TheOddsApiClient) -> None:
        self.session = session
        self.client = client
        self.odds_repo = OddsRepository(session)
        self.mapper = TheOddsApiMapper()

    async def _candidate_teams(self) -> list[tuple[int, str]]:
        result = await self.session.execute(select(Team.id, Team.name))
        return [(row[0], row[1]) for row in result.fetchall()]

    async def _scheduled_matches(self) -> list[Match]:
        result = await self.session.execute(
            select(Match).where(Match.status == "scheduled")
        )
        return list(result.scalars().all())

    async def ingest_odds_for_sport(self, sport_key: str) -> dict:
        """
        Trae todas las cuotas disponibles para una competición y las cruza
        contra los partidos programados que ya tenés en la base, por
        nombre de equipo normalizado + proximidad de fecha.
        """
        events = await self.client.get_odds(sport_key=sport_key)
        candidates = await self._candidate_teams()
        scheduled = await self._scheduled_matches()

        matched = 0
        created_total = 0
        unmatched = 0

        for event in events:
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")
            commence_time = event.get("commence_time", "")

            home_id = self.mapper.find_matching_team(home_name, candidates)
            away_id = self.mapper.find_matching_team(away_name, candidates)

            if not home_id or not away_id:
                unmatched += 1
                continue

            target_match = next(
                (
                    m for m in scheduled
                    if m.home_team_id == home_id and m.away_team_id == away_id
                    and self.mapper.is_same_match_date(commence_time, m.match_date)
                ),
                None,
            )

            if not target_match:
                unmatched += 1
                continue

            rows = self.mapper.extract_odds_rows(event)
            for row in rows:
                odds = Odds(match_id=target_match.id, is_closing=False, **row)
                await self.odds_repo.create(odds)
                created_total += 1

            matched += 1

        await self.session.commit()

        logger.info(
            "Cuotas ingeridas (The Odds API) | sport={} | eventos_matcheados={} | filas_creadas={} | sin_match={}",
            sport_key, matched, created_total, unmatched,
        )

        return {
            "sport_key": sport_key,
            "events_matched": matched,
            "odds_created": created_total,
            "events_unmatched": unmatched,
        }