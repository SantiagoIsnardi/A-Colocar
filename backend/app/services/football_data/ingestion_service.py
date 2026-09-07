from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.team_repository import TeamRepository
from app.services.football_data.client import FootballDataClient
from app.services.football_data.mapper import FootballDataMapper


class FootballDataIngestionService:

    def __init__(self, session: AsyncSession, client: FootballDataClient) -> None:
        self.session = session
        self.client = client
        self.team_repo = TeamRepository(session)
        self.match_repo = MatchRepository(session)
        self.mapper = FootballDataMapper()

    async def _get_or_create_team(self, team_data: dict) -> object:
        external_id = str(team_data["id"])
        team = await self.team_repo.get_by_external_id(external_id, "football_data")
        if not team:
            team = self.mapper.team_from_api(team_data)
            team = await self.team_repo.create(team)
            logger.info("Equipo creado (football-data.org): {} (id={})", team.name, team.id)
        return team

    async def ingest_competition_matches(
        self,
        competition_code: str,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        season: int | None = None,
    ) -> dict:
        response = await self.client.get_matches(
            competition_code=competition_code,
            status=status,
            date_from=date_from,
            date_to=date_to,
            season=season,
        )

        matches = response.get("matches", [])
        created = 0
        skipped = 0
        match_ids: list[int] = []

        for match_data in matches:
            ext_id = str(match_data["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "football_data")
            if existing:
                skipped += 1
                match_ids.append(existing.id)
                continue

            home_team = await self._get_or_create_team(match_data["homeTeam"])
            away_team = await self._get_or_create_team(match_data["awayTeam"])

            match = self.mapper.match_from_api(
                match_data=match_data,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            match = await self.match_repo.create(match)
            match_ids.append(match.id)
            created += 1

        await self.session.commit()

        logger.info(
            "Ingesta football-data.org | competición={} | temporada={} | creados={} | omitidos={}",
            competition_code, season or "actual", created, skipped,
        )

        return {
            "competition_code": competition_code,
            "season": season or "actual",
            "matches_created": created,
            "matches_skipped": skipped,
            "match_ids": match_ids,
        }

    async def sync_match_statuses(self, competition_code: str) -> dict:
        """
        Actualiza status y resultado de partidos ya existentes en la base,
        sin insertar nuevos. Necesario porque ingest_competition_matches
        solo inserta — nunca refresca un partido que pasó de 'scheduled'
        a 'finished' con el correr de los días.
        """
        response = await self.client.get_matches(competition_code=competition_code)
        matches = response.get("matches", [])

        updated = 0
        unchanged = 0
        not_found = 0

        for match_data in matches:
            ext_id = str(match_data["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "football_data")

            if not existing:
                not_found += 1
                continue

            fresh = self.mapper.match_from_api(
                match_data=match_data,
                home_team_id=existing.home_team_id,
                away_team_id=existing.away_team_id,
            )

            changed = (
                existing.status != fresh.status
                or existing.home_score != fresh.home_score
                or existing.away_score != fresh.away_score
                or existing.match_date != fresh.match_date
            )

            if changed:
                existing.status = fresh.status
                existing.home_score = fresh.home_score
                existing.away_score = fresh.away_score
                existing.match_date = fresh.match_date
                updated += 1
            else:
                unchanged += 1

        await self.session.commit()

        logger.info(
            "Sync de estados | competición={} | actualizados={} | sin_cambios={} | no_encontrados={}",
            competition_code, updated, unchanged, not_found,
        )

        return {
            "competition_code": competition_code,
            "matches_updated": updated,
            "matches_unchanged": unchanged,
            "matches_not_found": not_found,
        }