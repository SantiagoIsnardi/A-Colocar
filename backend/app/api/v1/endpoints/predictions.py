from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError, InsufficientDataError, InvalidRequestError
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.session import get_db
from app.services.prediction.prediction_engine import PredictionEngine

router = APIRouter(prefix="/predictions", tags=["predictions"])

VALID_MARKETS = {"corners", "yellow_cards", "fouls", "shots"}

DEFAULT_LINES_BY_MARKET = {
    "corners": [6.5, 7.5, 8.5, 9.5, 10.5],
    "yellow_cards": [1.5, 2.5, 3.5, 4.5],
    "fouls": [15.5, 20.5, 25.5, 30.5],
    "shots": [15.5, 20.5, 25.5],
}


@router.post("/matches/{match_id}/goals")
async def generate_goal_predictions(
    match_id: int,
    use_context: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> dict:
    engine = PredictionEngine(db)
    result = await engine.predict_goals(match_id=match_id, use_context=use_context)
    if "error" in result:
        raise DataNotFoundError(result["error"])
    return result


@router.post("/matches/{match_id}/markets/{market}")
async def generate_market_predictions(
    match_id: int,
    market: str,
    lines: list[float] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if market not in VALID_MARKETS:
        raise InvalidRequestError(f"Mercado inválido: {market!r}. Válidos: {sorted(VALID_MARKETS)}")

    active_lines = lines or DEFAULT_LINES_BY_MARKET[market]

    engine = PredictionEngine(db)
    result = await engine.predict_market(match_id=match_id, market=market, lines=active_lines)
    if "error" in result:
        raise InsufficientDataError(result["error"])
    return result


@router.get("/matches/{match_id}")
async def get_predictions(
    match_id: int,
    market: str = "goals",
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = PredictionRepository(db)
    predictions = await repo.get_latest_by_match(match_id=match_id, market=market)

    if not predictions:
        raise DataNotFoundError(
            f"Sin predicciones para mercado {market!r} — generarlas primero con POST"
        )

    return {
        "match_id": match_id,
        "market": market,
        "predictions": [
            {
                "line": float(p.line),
                "probability_over": float(p.probability_over),
                "percentage": round(float(p.probability_over) * 100, 1),
                "confidence_level": p.confidence_level,
                "model_version": p.model_version,
                "computed_at": p.computed_at.isoformat(),
            }
            for p in predictions
        ],
    }