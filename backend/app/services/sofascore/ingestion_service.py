"""
Servicio de ingesta de Sofascore. Trae fixtures + estadísticas de una
liga/temporada y las persiste, cruzando equipos por nombre normalizado
contra los que ya existen en la base (reutiliza la misma lógica de
normalización que TheOddsApiMapper, para no duplicar código).

source='sofascore' — convive sin conflicto con api_football, football_data
y manual_test gracias a la columna source ya presente en Team y Match.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.match import Match, MatchStatus
from app.db.models.team import Team
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.team_repository import TeamRepository
from app.services.odds.the_odds_api_mapper import TheOddsApiMapper
from app.services.sofascore.client import SofascoreClient
from app.services.sofascore.mapper import SofascoreMapper

_SOFASCORE_STATUS_MAP: dict[str, MatchStatus] = {
    "finished": MatchStatus.finished,
    "notstarted": MatchStatus.scheduled,
    "inprogress": MatchStatus.live,
    "postponed": MatchStatus.postponed,
    "canceled": MatchStatus.cancelled,
    "cancelled": MatchStatus.cancelled,
}


class SofascoreIngestionService:

    def __init__(self, session: AsyncSession, client: SofascoreClient) -> None:
        self.session = session
        self.client = client
        self.team_repo = TeamRepository(session)
        self.match_repo = MatchRepository(session)
        self.stats_repo = StatisticsRepository(session)
        self.name_matcher = TheOddsApiMapper()

    async def _all_teams(self) -> list[tuple[int, str]]:
        result = await self.session.execute(select(Team.id, Team.name))
        return [(row[0], row[1]) for row in result.fetchall()]

    async def _resolve_or_create_team(
        self, sofascore_team_data: dict, known_teams: list[tuple[int, str]]
    ) -> int:
        """
        Intenta encontrar el equipo por nombre normalizado entre los ya
        existentes. Si no hay match, crea uno nuevo con source='sofascore'.
        """
        name = sofascore_team_data["name"]
        matched_id = self.name_matcher.find_matching_team(name, known_teams)
        if matched_id:
            return matched_id

        sofascore_ext_id = str(sofascore_team_data["id"])
        existing = await self.team_repo.get_by_external_id(sofascore_ext_id, "sofascore")
        if existing:
            return existing.id

        new_team = Team(
            external_id=sofascore_ext_id,
            source="sofascore",
            name=name,
            short_name=sofascore_team_data.get("shortName"),
            country=(sofascore_team_data.get("country") or {}).get("name"),
        )
        created = await self.team_repo.create(new_team)
        logger.info("Equipo creado (Sofascore): {} (id={})", created.name, created.id)
        known_teams.append((created.id, created.name))
        return created.id

    async def ingest_league_season(
        self,
        league: str,
        year: str,
        max_matches: int | None = None,
        with_statistics: bool = True,
    ) -> dict:
        """
        Trae partidos finalizados de una liga/temporada de Sofascore,
        los persiste, y opcionalmente trae también sus estadísticas
        detalladas (corners, tarjetas, faltas, tiros).
        """
        raw_matches = self.client.get_match_dicts(year=year, league=league)
        finished = [m for m in raw_matches if m.get("status", {}).get("type") == "finished"]

        if max_matches:
            finished = finished[:max_matches]

        known_teams = await self._all_teams()

        matches_created = 0
        matches_skipped = 0
        stats_created = 0
        stats_failed = 0

        for raw in finished:
            ext_id = str(raw["id"])
            existing_match = await self.match_repo.get_by_external_id(ext_id, "sofascore")

            if existing_match:
                matches_skipped += 1
                match_obj = existing_match
            else:
                home_id = await self._resolve_or_create_team(raw["homeTeam"], known_teams)
                away_id = await self._resolve_or_create_team(raw["awayTeam"], known_teams)

                status = _SOFASCORE_STATUS_MAP.get(
                    raw.get("status", {}).get("type", ""), MatchStatus.scheduled
                )
                match_date = datetime.fromtimestamp(raw["startTimestamp"], tz=timezone.utc)

                match_obj = Match(
                    external_id=ext_id,
                    source="sofascore",
                    home_team_id=home_id,
                    away_team_id=away_id,
                    league=raw.get("tournament", {}).get("name", league),
                    season=year,
                    match_date=match_date,
                    venue=(raw.get("venue") or {}).get("name"),
                    status=status,
                    home_score=raw.get("homeScore", {}).get("current"),
                    away_score=raw.get("awayScore", {}).get("current"),
                )
                match_obj = await self.match_repo.create(match_obj)
                matches_created += 1

            if with_statistics:
                already_has_stats = await self.stats_repo.get_by_match(match_obj.id)
                if already_has_stats:
                    continue

                try:
                    stats_df = self.client.get_team_match_stats(int(ext_id))
                    stat_objects = SofascoreMapper.statistics_from_match(
                        stats_df=stats_df,
                        match_id=match_obj.id,
                        home_team_id=match_obj.home_team_id,
                        away_team_id=match_obj.away_team_id,
                        home_goals=match_obj.home_score or 0,
                        away_goals=match_obj.away_score or 0,
                    )
                    for stat in stat_objects:
                        self.session.add(stat)
                    stats_created += 1
                except Exception as exc:
                    logger.error("Error trayendo stats de Sofascore para match {}: {}", ext_id, exc)
                    stats_failed += 1

        await self.session.commit()

        logger.info(
            "Ingesta Sofascore | liga={} temporada={} | partidos_creados={} | omitidos={} | stats_creadas={} | stats_fallidas={}",
            league, year, matches_created, matches_skipped, stats_created, stats_failed,
        )

        return {
            "league": league,
            "year": year,
            "matches_created": matches_created,
            "matches_skipped": matches_skipped,
            "statistics_created": stats_created,
            "statistics_failed": stats_failed,
        }

    async def ingest_upcoming_matches(
        self,
        league: str,
        year: str,
        max_matches: int | None = None,
    ) -> dict:
        """
        Trae partidos programados (aún no jugados) de una liga/temporada.
        A diferencia de ingest_league_season, no busca estadísticas —
        un partido que no se jugó no tiene stats que traer.
        """
        raw_matches = self.client.get_match_dicts(year=year, league=league)
        upcoming = [
            m for m in raw_matches
            if m.get("status", {}).get("type") == "notstarted"
        ]

        if max_matches:
            upcoming = upcoming[:max_matches]

        known_teams = await self._all_teams()

        matches_created = 0
        matches_skipped = 0
        match_ids: list[int] = []

        for raw in upcoming:
            ext_id = str(raw["id"])
            existing_match = await self.match_repo.get_by_external_id(ext_id, "sofascore")

            if existing_match:
                matches_skipped += 1
                match_ids.append(existing_match.id)
                continue

            home_id = await self._resolve_or_create_team(raw["homeTeam"], known_teams)
            away_id = await self._resolve_or_create_team(raw["awayTeam"], known_teams)

            match_date = datetime.fromtimestamp(raw["startTimestamp"], tz=timezone.utc)

            match_obj = Match(
                external_id=ext_id,
                source="sofascore",
                home_team_id=home_id,
                away_team_id=away_id,
                league=raw.get("tournament", {}).get("name", league),
                season=year,
                match_date=match_date,
                venue=(raw.get("venue") or {}).get("name"),
                status=MatchStatus.scheduled,
                home_score=None,
                away_score=None,
            )
            match_obj = await self.match_repo.create(match_obj)
            match_ids.append(match_obj.id)
            matches_created += 1

        await self.session.commit()

        logger.info(
            "Ingesta próximos partidos Sofascore | liga={} temporada={} | creados={} | omitidos={}",
            league, year, matches_created, matches_skipped,
        )

        return {
            "league": league,
            "year": year,
            "matches_created": matches_created,
            "matches_skipped": matches_skipped,
            "match_ids": match_ids,
        }