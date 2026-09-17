from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.match import MatchStatus
from app.db.repositories.match_repository import MatchRepository
from app.db.session import get_db

router = APIRouter(prefix="/matches", tags=["matches"])

@router.get("/by-date")
async def get_matches_by_date(
    date: str | None = Query(default=None, description="DD-MM-YYYY, default hoy (horario Argentina)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Partidos programados/jugados en una fecha dada, en horario Argentina."""
    from datetime import date as date_cls, datetime, timedelta
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from app.db.models.team import Team

    ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

    target = date_cls.fromisoformat(date) if date else datetime.now(ARG_TZ).date()

    # Límites del día en horario argentino, convertidos a UTC para filtrar
    # contra match_date (que se guarda en UTC).
    start_arg = datetime.combine(target, datetime.min.time(), tzinfo=ARG_TZ)
    end_arg = start_arg + timedelta(days=1)
    start_utc = start_arg.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end_utc = end_arg.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    repo = MatchRepository(db)
    matches = await repo.get_by_date_range(start_utc, end_utc)

    team_ids = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
    teams_result = await db.execute(select(Team.id, Team.name).where(Team.id.in_(team_ids)))
    team_names = dict(teams_result.all())

    return {
        "date": target.isoformat(),
        "count": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team": team_names.get(m.home_team_id, f"#{m.home_team_id}"),
                "away_team": team_names.get(m.away_team_id, f"#{m.away_team_id}"),
                "league": m.league,
                "match_date_utc": m.match_date.isoformat(),
                "match_time_arg": m.match_date.replace(tzinfo=ZoneInfo("UTC"))
                    .astimezone(ARG_TZ).strftime("%H:%M"),
                "status": m.status,
                "home_score": m.home_score,
                "away_score": m.away_score,
            }
            for m in matches
        ],
    }

@router.get("/team/{team_id}")
async def get_matches_by_team(
    team_id: int,
    status: str | None = Query(default=None, description="scheduled | live | finished | postponed | cancelled"),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Historial o próximos partidos de un equipo, según el filtro de status."""
    from sqlalchemy import select

    from app.db.models.team import Team

    repo = MatchRepository(db)

    match_status = None
    if status:
        try:
            match_status = MatchStatus(status)
        except ValueError:
            pass  # status inválido — se ignora el filtro en vez de romper

    matches = await repo.get_by_team(team_id=team_id, status=match_status, limit=limit)

    team_ids = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
    teams_result = await db.execute(select(Team.id, Team.name).where(Team.id.in_(team_ids)))
    team_names = dict(teams_result.all())

    return {
        "team_id": team_id,
        "status_filter": status,
        "count": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team": team_names.get(m.home_team_id, f"#{m.home_team_id}"),
                "away_team": team_names.get(m.away_team_id, f"#{m.away_team_id}"),
                "league": m.league,
                "season": m.season,
                "match_date": m.match_date.isoformat(),
                "status": m.status,
                "home_score": m.home_score,
                "away_score": m.away_score,
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