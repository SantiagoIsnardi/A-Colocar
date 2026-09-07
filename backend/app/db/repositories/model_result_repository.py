from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.model_result import ModelResult


class ModelResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, result: ModelResult) -> ModelResult:
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def exists_for_prediction(self, prediction_id: int) -> bool:
        result = await self.session.execute(
            select(ModelResult.id).where(ModelResult.prediction_id == prediction_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_model_version(self, model_version: str) -> list[ModelResult]:
        result = await self.session.execute(
            select(ModelResult).where(ModelResult.model_version == model_version)
        )
        return list(result.scalars().all())

    async def get_by_market(self, market: str) -> list[ModelResult]:
        result = await self.session.execute(
            select(ModelResult).where(ModelResult.market == market)
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[ModelResult]:
        result = await self.session.execute(select(ModelResult))
        return list(result.scalars().all())