from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.value_bet_repository import ValueBetRepository
from app.db.session import get_db

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/markets")
async def get_rankings_by_market(
    limit_per_market: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Value bets abiertas, agrupadas y rankeadas por mercado — vista para la sección de rankings del frontend."""
    repo = ValueBetRepository(db)
    by_market = await repo.get_rankings_by_market(limit_per_market=limit_per_market)

    return {
        "markets": {
            market: [
                {
                    "id": b.id,
                    "match_id": b.match_id,
                    "line": float(b.line),
                    "side": b.side,
                    "edge": float(b.edge),
                    "edge_percentage": round(float(b.edge) * 100, 2),
                    "expected_value": float(b.expected_value),
                    "kelly_stake_pct": float(b.kelly_stake_pct) if b.kelly_stake_pct else None,
                    "price": float(b.price),
                }
                for b in bets
            ]
            for market, bets in by_market.items()
        }
    }