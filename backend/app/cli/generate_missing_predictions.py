"""
Uso:
    python -m app.cli.generate_missing_predictions

Genera predicciones (los 5 mercados) para todos los partidos 'scheduled'
que todavía no las tengan.
"""

import asyncio

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services.prediction.auto_predictor import AutoPredictor


async def main() -> None:
    setup_logging()

    predictor = AutoPredictor(AsyncSessionLocal)
    result = await predictor.generate_missing()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())