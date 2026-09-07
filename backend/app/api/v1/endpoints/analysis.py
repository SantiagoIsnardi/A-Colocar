import uuid
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AnalysisInProgressError, DataNotFoundError
from app.db.models.match import Match
from app.db.session import get_db
from app.tasks.analysis_store import analysis_store
from app.tasks.background_jobs import run_full_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/matches/{match_id}")
async def start_analysis(
    match_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Dispara el pipeline completo de análisis en background. Valida que el
    partido exista antes de aceptar la tarea, para fallar rápido en vez
    de crear un task_id que inevitablemente va a terminar en error.
    """
    result = await db.execute(select(Match.id).where(Match.id == match_id))
    if result.scalar_one_or_none() is None:
        raise DataNotFoundError(f"Partido {match_id} no encontrado")

    if analysis_store.is_match_in_progress(match_id):
        raise AnalysisInProgressError(f"Ya hay un análisis en curso para el partido {match_id}")

    task_id = str(uuid.uuid4())
    analysis_store.create(task_id, match_id)
    background_tasks.add_task(run_full_analysis, task_id, match_id)

    return {
        "task_id": task_id,
        "match_id": match_id,
        "status": "pending",
        "message": "Análisis en curso — consultar GET /analysis/{task_id} para el resultado",
    }


@router.get("/{task_id}")
async def get_analysis_status(task_id: str) -> dict:
    entry = analysis_store.get(task_id)
    if not entry:
        raise DataNotFoundError(f"Task {task_id} no encontrada")
    return entry