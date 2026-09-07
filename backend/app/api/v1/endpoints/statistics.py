from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientDataError
from app.db.session import get_db
from app.services.statistics.calculator import StatisticsCalculator
from app.services.statistics.frequency_analyzer import FrequencyAnalyzer

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/teams/{team_id}")
async def get_team_stats(
    team_id: int,
    last_n: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    calculator = StatisticsCalculator(db)
    result = await calculator.get_team_stats(team_id=team_id, last_n=last_n)
    if "error" in result:
        raise InsufficientDataError(result["error"])
    return result


@router.get("/teams/{team_id}/totals")
async def get_match_totals(
    team_id: int,
    last_n: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    calculator = StatisticsCalculator(db)
    result = await calculator.get_match_totals_aggregated(team_id=team_id, last_n=last_n)
    if "error" in result:
        raise InsufficientDataError(result["error"])
    return result


@router.get("/teams/{team_id}/frequencies")
async def get_frequencies(
    team_id: int,
    last_n: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    calculator = StatisticsCalculator(db)
    analyzer = FrequencyAnalyzer(calculator)
    result = await analyzer.analyze(team_id=team_id, last_n=last_n)
    if "error" in result:
        raise InsufficientDataError(result["error"])
    return result