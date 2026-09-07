from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.odds import Odds


class OddsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, odds: Odds) -> Odds:
        self.session.add(odds)
        await self.session.flush()
        await self.session.refresh(odds)
        return odds

    async def get_latest_by_match(self, match_id: int, market: str | None = None) -> list[Odds]:
        """Cuota más reciente por cada (línea, lado) para un partido."""
        stmt = (
            select(Odds)
            .where(Odds.match_id == match_id)
            .order_by(Odds.line, Odds.side, Odds.captured_at.desc())
        )
        if market:
            stmt = stmt.where(Odds.market == market)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        latest: dict[tuple[float, str], Odds] = {}
        for row in rows:
            key = (float(row.line), row.side)
            if key not in latest:
                latest[key] = row

        return sorted(latest.values(), key=lambda o: (float(o.line), o.side))

    async def get_closing_odds(self, match_id: int, market: str, line: float, side: str) -> Odds | None:
        result = await self.session.execute(
            select(Odds)
            .where(
                Odds.match_id == match_id,
                Odds.market == market,
                Odds.line == line,
                Odds.side == side,
                Odds.is_closing.is_(True),
            )
            .order_by(Odds.captured_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, match_id: int, market: str, line: float, side: str) -> list[Odds]:
        result = await self.session.execute(
            select(Odds)
            .where(
                Odds.match_id == match_id,
                Odds.market == market,
                Odds.line == line,
                Odds.side == side,
            )
            .order_by(Odds.captured_at.asc())
        )
        return list(result.scalars().all())