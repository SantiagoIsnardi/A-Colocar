from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_id: str, source: str) -> Match | None:
        result = await self.session.execute(
            select(Match).where(Match.external_id == external_id, Match.source == source)
        )
        return result.scalar_one_or_none()

    async def create(self, match: Match) -> Match:
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
        return match

    async def get_by_team(
        self,
        team_id: int,
        status: MatchStatus | None = None,
        limit: int = 20,
    ) -> list[Match]:
        stmt = (
            select(Match)
            .where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Match.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())