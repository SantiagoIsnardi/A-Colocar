"""
Genera automáticamente predicciones (los 5 mercados) para partidos
'scheduled' que todavía no las tengan. Así Predicciones muestra
resultados al instante al elegir cualquier mercado, y Rendimiento
mide sobre una muestra representativa, no solo la que el usuario
decide chequear a mano.

No regenera nada que ya exista — si querés una versión más nueva de
una predicción puntual, se sigue haciendo a mano desde Predicciones.
"""

import asyncio

from app.core.logging import logger
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.services.prediction.prediction_engine import PredictionEngine

DEFAULT_LINES_BY_MARKET = {
    "corners": [6.5, 7.5, 8.5, 9.5, 10.5],
    "yellow_cards": [1.5, 2.5, 3.5, 4.5],
    "fouls": [15.5, 20.5, 25.5, 30.5],
    "shots": [15.5, 20.5, 25.5],
}

ALL_MARKETS = ["goals", "corners", "yellow_cards", "fouls", "shots"]

# Cada tantos partidos, se cierra la conexión y se abre una nueva.
# Ni una sola para los 700 (se muere a mitad de camino en Neon free
# tier) ni una nueva por cada intento (satura DNS en red hogareña).
BATCH_SIZE = 20

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 3


class AutoPredictor:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    async def generate_missing(self) -> dict:
        async with self.session_factory() as session:
            scheduled_ids = [m.id for m in await MatchRepository(session).get_scheduled()]
            existing_pairs = await PredictionRepository(session).get_existing_match_market_pairs()

        pending = [
            (match_id, market)
            for match_id in scheduled_ids
            for market in ALL_MARKETS
            if (match_id, market) not in existing_pairs
        ]

        generated = 0
        skipped_error = 0
        session = None

        for i, (match_id, market) in enumerate(pending):
            if i % BATCH_SIZE == 0:
                if session is not None:
                    await session.close()
                session = self.session_factory()

            ok = await self._predict_with_retry(session, match_id, market)
            if ok:
                generated += 1
            else:
                skipped_error += 1

        if session is not None:
            await session.close()

        return {
            "matches_checked": len(scheduled_ids),
            "predictions_generated": generated,
            "skipped_existing": len(scheduled_ids) * len(ALL_MARKETS) - len(pending),
            "skipped_error": skipped_error,
        }

    async def _predict_with_retry(self, session, match_id: int, market: str) -> bool:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                engine = PredictionEngine(session)
                if market == "goals":
                    result = await engine.predict_goals(match_id=match_id)
                else:
                    result = await engine.predict_market(
                        match_id=match_id, market=market, lines=DEFAULT_LINES_BY_MARKET[market],
                    )

                if "error" in result:
                    return False  # dato insuficiente, no es un error de red: no reintentar

                await session.commit()
                return True

            except Exception as exc:
                await session.rollback()
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "AutoPredictor | reintento {}/{} match {} mercado {}: {}",
                        attempt, MAX_RETRIES, match_id, market, exc,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(
                        "AutoPredictor | error definitivo match {} mercado {}: {}",
                        match_id, market, exc,
                    )
                    return False
        return False