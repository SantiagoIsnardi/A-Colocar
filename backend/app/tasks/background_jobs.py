"""
Job de análisis completo en background: corre goles + mercados extra +
value bets para un partido en una sola tarea, sin bloquear el request
HTTP que la disparó. La sesión de base de datos se crea de forma
independiente a la del request original.
"""

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.services.prediction.prediction_engine import PredictionEngine
from app.services.value.value_finder import ValueFinder
from app.tasks.analysis_store import analysis_store

EXTRA_MARKETS = ["corners", "yellow_cards", "fouls", "shots"]

DEFAULT_LINES_BY_MARKET = {
    "corners": [6.5, 7.5, 8.5, 9.5, 10.5],
    "yellow_cards": [1.5, 2.5, 3.5, 4.5],
    "fouls": [15.5, 20.5, 25.5, 30.5],
    "shots": [15.5, 20.5, 25.5],
}


async def run_full_analysis(task_id: str, match_id: int) -> None:
    """
    Pipeline completo: predicciones de goles, predicciones de mercados
    adicionales (si hay datos suficientes), y búsqueda de value bets
    sobre cada mercado con cuotas disponibles.
    """
    analysis_store.set_running(task_id)

    try:
        async with AsyncSessionLocal() as session:
            engine = PredictionEngine(session)
            finder = ValueFinder(session)

            summary: dict = {"match_id": match_id, "markets": {}}

            goals_result = await engine.predict_goals(match_id=match_id)
            if "error" not in goals_result:
                summary["markets"]["goals"] = {
                    "confidence_level": goals_result["confidence_level"],
                    "sample_size": goals_result["sample_size"],
                }
                value_result = await finder.find_value_bets(match_id=match_id, market="goals")
                if "error" not in value_result:
                    summary["markets"]["goals"]["value_bets_found"] = value_result["value_bets_found"]
            else:
                summary["markets"]["goals"] = {"error": goals_result["error"]}

            for market in EXTRA_MARKETS:
                lines = DEFAULT_LINES_BY_MARKET[market]
                market_result = await engine.predict_market(match_id=match_id, market=market, lines=lines)

                if "error" in market_result:
                    summary["markets"][market] = {"error": market_result["error"]}
                    continue

                summary["markets"][market] = {
                    "confidence_level": market_result["confidence_level"],
                    "sample_size": market_result["sample_size"],
                }

                value_result = await finder.find_value_bets(match_id=match_id, market=market)
                if "error" not in value_result:
                    summary["markets"][market]["value_bets_found"] = value_result["value_bets_found"]

            analysis_store.set_completed(task_id, summary)
            logger.info("Análisis completo finalizado | task={} | match={}", task_id, match_id)

    except Exception as exc:
        logger.error("Fallo en análisis background | task={} | match={} | error={}", task_id, match_id, str(exc))
        analysis_store.set_failed(task_id, str(exc))