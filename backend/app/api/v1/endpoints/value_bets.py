from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.repositories.value_bet_repository import ValueBetRepository
from app.db.session import get_db
from app.services.value.value_finder import ValueFinder

router = APIRouter(prefix="/value-bets", tags=["value-bets"])


@router.post("/matches/{match_id}/find")
async def find_value_bets(
    match_id: int,
    market: str = "goals",
    db: AsyncSession = Depends(get_db),
) -> dict:
    finder = ValueFinder(db)
    result = await finder.find_value_bets(match_id=match_id, market=market)
    if "error" in result:
        raise DataNotFoundError(result["error"])
    return result


@router.get("/open")
async def get_open_value_bets(
    market: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = ValueBetRepository(db)
    bets = await repo.get_open_ranked_by_edge(market=market, limit=limit)

    return {
        "count": len(bets),
        "value_bets": [
            {
                "id": b.id,
                "match_id": b.match_id,
                "market": b.market,
                "line": float(b.line),
                "side": b.side,
                "probability_model": float(b.probability_model),
                "probability_implied": float(b.probability_implied),
                "edge": float(b.edge),
                "edge_percentage": round(float(b.edge) * 100, 2),
                "expected_value": float(b.expected_value),
                "kelly_stake_pct": float(b.kelly_stake_pct) if b.kelly_stake_pct else None,
                "price": float(b.price),
                "status": b.status,
                "detected_at": b.detected_at.isoformat(),
            }
            for b in bets
        ],
    }


@router.get("/matches/{match_id}")
async def get_match_value_bets(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = ValueBetRepository(db)
    bets = await repo.get_by_match(match_id=match_id)

    return {
        "match_id": match_id,
        "count": len(bets),
        "value_bets": [
            {
                "id": b.id,
                "market": b.market,
                "line": float(b.line),
                "side": b.side,
                "edge": float(b.edge),
                "edge_percentage": round(float(b.edge) * 100, 2),
                "expected_value": float(b.expected_value),
                "kelly_stake_pct": float(b.kelly_stake_pct) if b.kelly_stake_pct else None,
                "price": float(b.price),
                "status": b.status,
            }
            for b in bets
        ],
    }