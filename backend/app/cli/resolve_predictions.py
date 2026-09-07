"""
Uso:
    python -m app.cli.resolve_predictions
    python -m app.cli.resolve_predictions 66

Sin argumento: resuelve todas las predicciones pendientes de todos los
partidos finalizados. Con match_id: resuelve solo ese partido.
"""

import asyncio
import sys

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.calibration.calibration_engine import CalibrationEngine


async def main(match_id: int | None) -> None:
    setup_logging()

    async with AsyncSessionLocal() as session:
        engine = CalibrationEngine(session)

        if match_id:
            result = await engine.resolve_match(match_id)
        else:
            result = await engine.resolve_all_pending()

        print(result)


if __name__ == "__main__":
    _match_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(main(_match_id))