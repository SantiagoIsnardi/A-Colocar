from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.session import get_db
from app.services.calibration.calibration_engine import CalibrationEngine

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.post("/matches/{match_id}/resolve")
async def resolve_match_predictions(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    engine = CalibrationEngine(db)
    result = await engine.resolve_match(match_id=match_id)
    if "error" in result:
        raise DataNotFoundError(result["error"])
    return result


@router.post("/resolve-all")
async def resolve_all_pending(db: AsyncSession = Depends(get_db)) -> dict:
    engine = CalibrationEngine(db)
    return await engine.resolve_all_pending()


@router.get("/summary")
async def get_summary(
    model_version: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    engine = CalibrationEngine(db)
    return await engine.get_calibration_summary(model_version=model_version)