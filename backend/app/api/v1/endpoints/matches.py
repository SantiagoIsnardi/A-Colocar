from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.match import MatchStatus
from app.db.repositories.match_repository import MatchRepository
from app.db.session import get_db

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/team/{team_id}")
async def get_matches_by_team(
    team_id: int,
    status: str | None = Query(default=None, description="scheduled | live | finished | postponed | cancelled"),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Historial o próximos partidos de un equipo, según el filtro de status."""
    repo = MatchRepository(db)

    match_status = None
    if status:
        try:
            match_status = MatchStatus(status)
        except ValueError:
            pass  # status inválido — se ignora el filtro en vez de romper

    matches = await repo.get_by_team(team_id=team_id, status=match_status, limit=limit)

    return {
        "team_id": team_id,
        "status_filter": status,
        "count": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team_id": m.home_team_id,
                "away_team_id": m.away_team_id,
                "league": m.league,
                "season": m.season,
                "match_date": m.match_date.isoformat(),
                "status": m.status,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "source": m.source,
            }
            for m in matches
        ],
    }


@router.get("/{match_id}")
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    from sqlalchemy import select

    from app.db.models.match import Match

    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()

    if not match:
        raise DataNotFoundError(f"Partido {match_id} no encontrado")

    return {
        "id": match.id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "league": match.league,
        "season": match.season,
        "match_date": match.match_date.isoformat(),
        "venue": match.venue,
        "referee": match.referee,
        "status": match.status,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "source": match.source,
    }