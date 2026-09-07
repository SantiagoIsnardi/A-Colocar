"""
Almacén en memoria del estado de análisis en background. Suficiente para
un proyecto de instancia única — si en el futuro se necesita persistencia
entre reinicios o múltiples workers, este es el punto de reemplazo por
una tabla dedicada o Redis.
"""

import enum
import time
from typing import Any


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AnalysisStore:

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def create(self, task_id: str, match_id: int) -> None:
        self._store[task_id] = {
            "task_id": task_id,
            "match_id": match_id,
            "status": AnalysisStatus.pending,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

    def set_running(self, task_id: str) -> None:
        if task_id in self._store:
            self._store[task_id]["status"] = AnalysisStatus.running
            self._store[task_id]["updated_at"] = time.time()

    def set_completed(self, task_id: str, result: dict) -> None:
        if task_id in self._store:
            self._store[task_id]["status"] = AnalysisStatus.completed
            self._store[task_id]["result"] = result
            self._store[task_id]["updated_at"] = time.time()

    def set_failed(self, task_id: str, error: str) -> None:
        if task_id in self._store:
            self._store[task_id]["status"] = AnalysisStatus.failed
            self._store[task_id]["error"] = error
            self._store[task_id]["updated_at"] = time.time()

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self._store.get(task_id)

    def is_match_in_progress(self, match_id: int) -> bool:
        return any(
            entry["match_id"] == match_id and entry["status"] in (AnalysisStatus.pending, AnalysisStatus.running)
            for entry in self._store.values()
        )


# Instancia global — un solo store por proceso
analysis_store = AnalysisStore()