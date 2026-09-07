from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.value_bet import BetStatus, ValueBet


class ValueBetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, value_bet: ValueBet) -> ValueBet:
        self.session.add(value_bet)
        await self.session.flush()
        await self.session.refresh(value_bet)
        return value_bet

    async def get_by_match(self, match_id: int) -> list[ValueBet]:
        result = await self.session.execute(
            select(ValueBet).where(ValueBet.match_id == match_id).order_by(ValueBet.edge.desc())
        )
        return list(result.scalars().all())
    
    async def get_open_equivalent(
        self,
        match_id: int,
        market: str,
        line: float,
        side: str,
    ) -> ValueBet | None:
        """
        Busca una value bet abierta ya existente para la misma combinación
        exacta de partido, mercado, línea y lado. Usado para evitar duplicar
        la misma detección de valor cada vez que se re-corre el análisis
        sobre un partido que todavía no se jugó.
        """
        result = await self.session.execute(
            select(ValueBet).where(
                ValueBet.match_id == match_id,
                ValueBet.market == market,
                ValueBet.line == line,
                ValueBet.side == side,
                ValueBet.status == BetStatus.open,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_open_ranked_by_edge(self, market: str | None = None, limit: int = 50) -> list[ValueBet]:
        stmt = (
            select(ValueBet)
            .where(ValueBet.status == BetStatus.open)
            .order_by(ValueBet.edge.desc())
            .limit(limit)
        )
        if market:
            stmt = stmt.where(ValueBet.market == market)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_rankings_by_market(self, limit_per_market: int = 10) -> dict[str, list[ValueBet]]:
        result = await self.session.execute(
            select(ValueBet)
            .where(ValueBet.status == BetStatus.open)
            .order_by(ValueBet.market, ValueBet.edge.desc())
        )
        rows = result.scalars().all()

        by_market: dict[str, list[ValueBet]] = {}
        for row in rows:
            bucket = by_market.setdefault(row.market, [])
            if len(bucket) < limit_per_market:
                bucket.append(row)

        return by_market