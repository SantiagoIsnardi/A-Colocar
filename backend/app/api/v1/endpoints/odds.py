from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.repositories.odds_repository import OddsRepository
from app.db.session import get_db
from app.services.odds.implied_probability import ImpliedProbability
from app.services.odds.line_movement_tracker import LineMovementTracker

router = APIRouter(prefix="/odds", tags=["odds"])


@router.get("/matches/{match_id}")
async def get_match_odds(
    match_id: int,
    market: str = "goals",
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = OddsRepository(db)
    odds_list = await repo.get_latest_by_match(match_id=match_id, market=market)

    if not odds_list:
        raise DataNotFoundError(
            f"Sin cuotas para match {match_id} mercado {market!r} — usar seed_odds primero"
        )

    return {
        "match_id": match_id,
        "market": market,
        "odds": [
            {
                "line": float(o.line),
                "side": o.side,
                "price": float(o.price),
                "bookmaker": o.bookmaker,
                "captured_at": o.captured_at.isoformat(),
            }
            for o in odds_list
        ],
    }


@router.get("/matches/{match_id}/implied-probability")
async def get_implied_probability(
    match_id: int,
    market: str,
    line: float,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = OddsRepository(db)
    odds_list = await repo.get_latest_by_match(match_id=match_id, market=market)

    matching = [o for o in odds_list if float(o.line) == line]
    over_odds = next((o for o in matching if o.side == "over"), None)
    under_odds = next((o for o in matching if o.side == "under"), None)

    if not over_odds or not under_odds:
        raise DataNotFoundError(
            f"Falta cuota over o under para línea {line} en mercado {market!r}"
        )

    result = ImpliedProbability.clean_pair(float(over_odds.price), float(under_odds.price))

    return {
        "match_id": match_id,
        "market": market,
        "line": line,
        "price_over": float(over_odds.price),
        "price_under": float(under_odds.price),
        **result,
    }


@router.get("/matches/{match_id}/line-movement")
async def get_line_movement(
    match_id: int,
    market: str,
    line: float,
    side: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = OddsRepository(db)
    history = await repo.get_history(match_id=match_id, market=market, line=line, side=side)

    if not history:
        raise DataNotFoundError("Sin historial de cuotas para esa línea")

    movement = LineMovementTracker.calculate_movement(history)
    return {
        "match_id": match_id,
        "market": market,
        "line": line,
        "side": side,
        **movement,
    }