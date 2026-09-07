"""
Dependencias reutilizables de FastAPI, más allá de get_db (que ya vive
en app.db.session porque es específica de la conexión).
"""

from app.tasks.analysis_store import analysis_store


def get_analysis_store():
    return analysis_store