from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.repositories.team_repository import TeamRepository
from app.db.session import get_db

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/search")
async def search_teams(
    q: str = Query(..., min_length=2, description="Nombre o parte del nombre del equipo"),
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Búsqueda de equipos por nombre parcial, para autocompletado en el frontend."""
    repo = TeamRepository(db)
    teams = await repo.search_by_name(q, limit=limit)

    return {
        "query": q,
        "count": len(teams),
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "short_name": t.short_name,
                "country": t.country,
                "logo_url": t.logo_url,
                "source": t.source,
            }
            for t in teams
        ],
    }


@router.get("/{team_id}")
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    repo = TeamRepository(db)
    team = await repo.get_by_id(team_id)

    if not team:
        raise DataNotFoundError(f"Equipo {team_id} no encontrado")

    return {
        "id": team.id,
        "name": team.name,
        "short_name": team.short_name,
        "country": team.country,
        "league": team.league,
        "founded_year": team.founded_year,
        "logo_url": team.logo_url,
        "source": team.source,
    }