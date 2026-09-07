"""
Orquesta la resolución de predicciones: dado el resultado real de un
partido, marca cada predicción asociada como acertada o no, calcula su
Brier Score, y si hay una value bet vinculada con cuota de cierre
disponible, calcula también el CLV.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.match import Match, MatchStatus
from app.db.models.model_result import ModelResult
from app.db.models.prediction import Prediction
from app.db.models.value_bet import ValueBet
from app.db.repositories.model_result_repository import ModelResultRepository
from app.db.repositories.odds_repository import OddsRepository
from app.services.calibration.brier_score import BrierScore
from app.services.calibration.clv_tracker import CLVTracker


class CalibrationEngine:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.result_repo = ModelResultRepository(session)
        self.odds_repo = OddsRepository(session)

    async def _get_finished_matches_with_predictions(self) -> list[Match]:
        result = await self.session.execute(
            select(Match)
            .where(
                Match.status == MatchStatus.finished,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def _get_predictions_for_match(self, match_id: int) -> list[Prediction]:
        result = await self.session.execute(
            select(Prediction).where(Prediction.match_id == match_id)
        )
        return list(result.scalars().all())

    async def _get_value_bet_for_prediction(self, prediction_id: int) -> ValueBet | None:
        result = await self.session.execute(
            select(ValueBet).where(ValueBet.prediction_id == prediction_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _resolve_outcome(match: Match, market: str, line: float) -> bool | None:
        """
        Determina si un mercado 'over' se cumplió, dado el resultado real
        del partido. Por ahora soporta 'goals' — otros mercados (corners,
        tarjetas, faltas) requieren datos de Statistic que no siempre
        están disponibles para partidos ya resueltos vía football-data.org.
        """
        if market != "goals":
            return None
        if match.home_score is None or match.away_score is None:
            return None
        total_goals = match.home_score + match.away_score
        return total_goals > line

    async def resolve_match(self, match_id: int, limit_new: int | None = None) -> dict:
        result = await self.session.execute(select(Match).where(Match.id == match_id))
        match = result.scalar_one_or_none()

        if not match or match.status != MatchStatus.finished:
            return {"error": f"Partido {match_id} no encontrado o no finalizado"}

        predictions = await self._get_predictions_for_match(match_id)
        resolved_count = 0
        skipped_existing = 0
        skipped_unresolvable = 0

        for prediction in predictions:
            if await self.result_repo.exists_for_prediction(prediction.id):
                skipped_existing += 1
                continue

            actual_outcome = self._resolve_outcome(match, prediction.market, float(prediction.line))
            if actual_outcome is None:
                skipped_unresolvable += 1
                continue

            predicted_probability = float(prediction.probability_over)
            brier = BrierScore.calculate(predicted_probability, actual_outcome)

            value_bet = await self._get_value_bet_for_prediction(prediction.id)
            closing_prob = None
            clv_pct = None

            if value_bet:
                closing_odds = await self.odds_repo.get_closing_odds(
                    match_id=match_id,
                    market=prediction.market,
                    line=float(prediction.line),
                    side=value_bet.side,
                )
                if closing_odds:
                    closing_prob = 1 / float(closing_odds.price)
                    clv_pct = CLVTracker.calculate_clv(float(value_bet.price), float(closing_odds.price))

            model_result = ModelResult(
                prediction_id=prediction.id,
                match_id=match_id,
                value_bet_id=value_bet.id if value_bet else None,
                market=prediction.market,
                line=prediction.line,
                predicted_probability=predicted_probability,
                actual_outcome=actual_outcome,
                brier_score=brier,
                closing_probability_implied=round(closing_prob, 4) if closing_prob else None,
                clv_pct=clv_pct,
                model_version=prediction.model_version,
            )
            await self.result_repo.create(model_result)
            resolved_count += 1

            if limit_new and resolved_count >= limit_new:
                break

        await self.session.commit()

        logger.info(
            "Calibración | match={} | resueltas={} | ya_existentes={} | no_resolubles={}",
            match_id, resolved_count, skipped_existing, skipped_unresolvable,
        )

        return {
            "match_id": match_id,
            "resolved": resolved_count,
            "already_resolved": skipped_existing,
            "unresolvable": skipped_unresolvable,
        }

    async def resolve_all_pending(self) -> dict:
        """Resuelve todas las predicciones pendientes de todos los partidos ya finalizados."""
        matches = await self._get_finished_matches_with_predictions()

        total_resolved = 0
        matches_processed = 0

        for match in matches:
            result = await self.resolve_match(match.id)
            if "error" not in result:
                total_resolved += result["resolved"]
                matches_processed += 1

        return {
            "matches_processed": matches_processed,
            "total_predictions_resolved": total_resolved,
        }

    async def get_calibration_summary(self, model_version: str | None = None) -> dict:
        """
        Resumen agregado de calibración: Brier Score promedio, CLV promedio,
        y accuracy simple, opcionalmente filtrado por versión de modelo.
        """
        if model_version:
            results = await self.result_repo.get_by_model_version(model_version)
        else:
            results = await self.result_repo.get_all()

        if not results:
            return {
                "sample_size": 0,
                "note": "Sin resultados resueltos todavía — correr resolve_predictions primero",
            }

        brier_scores = [float(r.brier_score) for r in results]
        clv_values = [float(r.clv_pct) for r in results if r.clv_pct is not None]

        correct_predictions = sum(
            1 for r in results
            if (float(r.predicted_probability) >= 0.5) == r.actual_outcome
        )

        return {
            "sample_size": len(results),
            "avg_brier_score": BrierScore.average(brier_scores),
            "accuracy_simple": round(correct_predictions / len(results), 4),
            "avg_clv_percentage": round(sum(clv_values) / len(clv_values), 4) if clv_values else None,
            "clv_sample_size": len(clv_values),
            "model_version_filter": model_version or "todas",
        }