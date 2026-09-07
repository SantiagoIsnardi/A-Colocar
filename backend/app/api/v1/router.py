from fastapi import APIRouter

from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.calibration import router as calibration_router
from app.api.v1.endpoints.matches import router as matches_router
from app.api.v1.endpoints.odds import router as odds_router
from app.api.v1.endpoints.predictions import router as predictions_router
from app.api.v1.endpoints.rankings import router as rankings_router
from app.api.v1.endpoints.statistics import router as statistics_router
from app.api.v1.endpoints.teams import router as teams_router
from app.api.v1.endpoints.value_bets import router as value_bets_router

api_router = APIRouter()
api_router.include_router(teams_router)
api_router.include_router(matches_router)
api_router.include_router(statistics_router)
api_router.include_router(predictions_router)
api_router.include_router(odds_router)
api_router.include_router(value_bets_router)
api_router.include_router(calibration_router)
api_router.include_router(analysis_router)
api_router.include_router(rankings_router)