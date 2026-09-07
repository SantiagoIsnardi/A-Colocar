from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, prediction: Prediction) -> Prediction:
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)
        return prediction

    async def get_latest_by_match(self, match_id: int, market: str | None = None) -> list[Prediction]:
        """
        Devuelve la predicción más reciente por cada línea, para un partido
        (y opcionalmente un mercado específico).
        """
        stmt = (
            select(Prediction)
            .where(Prediction.match_id == match_id)
            .order_by(Prediction.line, Prediction.computed_at.desc())
        )
        if market:
            stmt = stmt.where(Prediction.market == market)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # quedarnos solo con la más reciente por línea
        latest_by_line: dict[float, Prediction] = {}
        for row in rows:
            line = float(row.line)
            if line not in latest_by_line:
                latest_by_line[line] = row

        return sorted(latest_by_line.values(), key=lambda p: float(p.line))