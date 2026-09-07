from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.statistic import Statistic


class StatisticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_match_and_team(self, match_id: int, team_id: int) -> Statistic | None:
        result = await self.session.execute(
            select(Statistic).where(
                Statistic.match_id == match_id,
                Statistic.team_id == team_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_match(self, match_id: int) -> list[Statistic]:
        result = await self.session.execute(
            select(Statistic).where(Statistic.match_id == match_id)
        )
        return list(result.scalars().all())

    async def get_by_team(self, team_id: int, limit: int = 30) -> list[Statistic]:
        result = await self.session.execute(
            select(Statistic)
            .where(Statistic.team_id == team_id)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, stat: Statistic) -> Statistic:
        self.session.add(stat)
        await self.session.flush()
        await self.session.refresh(stat)
        return stat

    async def matches_with_statistics(self) -> set[int]:
        result = await self.session.execute(
            select(Statistic.match_id).distinct()
        )
        return {row[0] for row in result.fetchall()}