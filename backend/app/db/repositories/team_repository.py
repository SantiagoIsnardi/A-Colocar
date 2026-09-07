from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.team import Team


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_id: str, source: str) -> Team | None:
        result = await self.session.execute(
            select(Team).where(Team.external_id == external_id, Team.source == source)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, team_id: int) -> Team | None:
        result = await self.session.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 10) -> list[Team]:
        result = await self.session.execute(
            select(Team).where(Team.name.ilike(f"%{name}%")).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, team: Team) -> Team:
        self.session.add(team)
        await self.session.flush()
        await self.session.refresh(team)
        return team