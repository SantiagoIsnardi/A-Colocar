from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.match import Match
from app.db.models.prediction import ConfidenceLevel, Prediction
from app.db.repositories.prediction_repository import PredictionRepository
from app.services.context.context_engine import ContextEngine
from app.services.prediction.dixon_coles import DixonColes
from app.services.prediction.market_models import MarketPredictor
from app.services.prediction.poisson_model import PoissonModel
from app.services.prediction.team_strength import TeamStrengthService

DEFAULT_GOAL_LINES = [0.5, 1.5, 2.5, 3.5, 4.5]
GOALS_MODEL_VERSION = "dixon_coles_context_v1"
MARKET_MODEL_VERSION = "poisson_market_v1"


class PredictionEngine:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.strength_service = TeamStrengthService(session)
        self.prediction_repo = PredictionRepository(session)
        self.market_predictor = MarketPredictor(session)
        self.context_engine = ContextEngine(session)
        self.model = PoissonModel()

    @staticmethod
    def _confidence_level(min_sample: int) -> ConfidenceLevel:
        if min_sample >= 20:
            return ConfidenceLevel.high
        if min_sample >= 10:
            return ConfidenceLevel.medium
        return ConfidenceLevel.low

    async def predict_goals(
        self,
        match_id: int,
        lines: list[float] | None = None,
        use_context: bool = True,
    ) -> dict:
        active_lines = lines or DEFAULT_GOAL_LINES

        match_result = await self.session.execute(select(Match).where(Match.id == match_id))
        match = match_result.scalar_one_or_none()
        if not match:
            return {"error": f"Partido {match_id} no encontrado"}

        league_avg = await self.strength_service.league_averages()

        home_strength = await self.strength_service.get_home_strength(match.home_team_id, league_avg)
        away_strength = await self.strength_service.get_away_strength(match.away_team_id, league_avg)

        min_sample = min(home_strength["sample_size"], away_strength["sample_size"])

        if not (home_strength["sufficient"] and away_strength["sufficient"]):
            logger.warning(
                "Muestra insuficiente para match {} | home_sample={} away_sample={}",
                match_id, home_strength["sample_size"], away_strength["sample_size"],
            )

        lambda_home = league_avg["avg_home_goals"] * home_strength["attack"] * away_strength["defense"]
        lambda_away = league_avg["avg_away_goals"] * away_strength["attack"] * home_strength["defense"]

        context = None
        if use_context:
            context = await self.context_engine.get_match_context(
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                referee_name=match.referee,
            )
            lambda_home *= context["home_attack_multiplier"]
            lambda_away *= context["away_attack_multiplier"]

        lambda_home = max(0.1, min(lambda_home, 6.0))
        lambda_away = max(0.1, min(lambda_away, 6.0))

        all_results = await self.strength_service.get_all_finished_results()
        rho = DixonColes.estimate_rho(
            results=all_results,
            lambda_home_avg=league_avg["avg_home_goals"],
            lambda_away_avg=league_avg["avg_away_goals"],
        )

        matrix = self.model.score_matrix(lambda_home, lambda_away, rho=rho)
        confidence = self._confidence_level(min_sample)

        model_params = {
            "lambda_home": round(lambda_home, 4),
            "lambda_away": round(lambda_away, 4),
            "rho": round(rho, 4),
            "home_attack": round(home_strength["attack"], 4),
            "home_defense": round(home_strength["defense"], 4),
            "away_attack": round(away_strength["attack"], 4),
            "away_defense": round(away_strength["defense"], 4),
            "league_avg_home_goals": round(league_avg["avg_home_goals"], 4),
            "league_avg_away_goals": round(league_avg["avg_away_goals"], 4),
            "context_applied": use_context,
        }
        if context:
            model_params["home_context_multiplier"] = context["home_attack_multiplier"]
            model_params["away_context_multiplier"] = context["away_attack_multiplier"]

        predictions_out = []
        for line in active_lines:
            probability_over = self.model.prob_over_total_goals(matrix, line)

            prediction = Prediction(
                match_id=match_id,
                market="goals",
                line=line,
                model_version=GOALS_MODEL_VERSION,
                probability_over=round(probability_over, 4),
                confidence_level=confidence,
                sample_size=min_sample,
                model_params=model_params,
            )
            await self.prediction_repo.create(prediction)

            predictions_out.append({
                "line": line,
                "label": f"Más de {line} goles",
                "probability_over": round(probability_over, 4),
                "percentage": round(probability_over * 100, 1),
            })

        await self.session.commit()

        logger.info(
            "Predicción goles | match={} | λ_home={:.2f} λ_away={:.2f} rho={:.3f} | confianza={} | contexto={}",
            match_id, lambda_home, lambda_away, rho, confidence.value, use_context,
        )

        result = {
            "match_id": match_id,
            "model_version": GOALS_MODEL_VERSION,
            "confidence_level": confidence.value,
            "sample_size": min_sample,
            "lambda_home": round(lambda_home, 4),
            "lambda_away": round(lambda_away, 4),
            "rho": round(rho, 4),
            "predictions": predictions_out,
        }
        if context:
            result["context"] = context

        return result

    async def predict_market(
        self,
        match_id: int,
        market: str,
        lines: list[float],
    ) -> dict:
        match_result = await self.session.execute(select(Match).where(Match.id == match_id))
        match = match_result.scalar_one_or_none()
        if not match:
            return {"error": f"Partido {match_id} no encontrado"}

        home_pred = await self.market_predictor.predict_market(
            team_id=match.home_team_id, market=market, lines=lines
        )
        away_pred = await self.market_predictor.predict_market(
            team_id=match.away_team_id, market=market, lines=lines
        )

        if "error" in home_pred or "error" in away_pred:
            errors = [p.get("error") for p in (home_pred, away_pred) if "error" in p]
            return {"error": "; ".join(errors)}

        combined_lambda = (home_pred["lambda_total"] + away_pred["lambda_total"]) / 2
        min_sample = min(home_pred["sample_size"], away_pred["sample_size"])
        confidence = self._confidence_level(min_sample)

        from scipy.stats import poisson as scipy_poisson

        predictions_out = []
        for line in lines:
            prob_over = 1 - scipy_poisson.cdf(int(line), combined_lambda)
            prob_over = max(0.0, min(float(prob_over), 1.0))

            prediction = Prediction(
                match_id=match_id,
                market=market,
                line=line,
                model_version=MARKET_MODEL_VERSION,
                probability_over=round(prob_over, 4),
                confidence_level=confidence,
                sample_size=min_sample,
                model_params={
                    "combined_lambda": round(combined_lambda, 4),
                    "home_lambda": round(home_pred["lambda_total"], 4),
                    "away_lambda": round(away_pred["lambda_total"], 4),
                },
            )
            await self.prediction_repo.create(prediction)

            predictions_out.append({
                "line": line,
                "label": f"Más de {line} {market}",
                "probability_over": round(prob_over, 4),
                "percentage": round(prob_over * 100, 1),
            })

        await self.session.commit()

        logger.info(
            "Predicción {} | match={} | λ_combinado={:.2f} | confianza={}",
            market, match_id, combined_lambda, confidence.value,
        )

        return {
            "match_id": match_id,
            "market": market,
            "model_version": MARKET_MODEL_VERSION,
            "confidence_level": confidence.value,
            "sample_size": min_sample,
            "combined_lambda": round(combined_lambda, 4),
            "predictions": predictions_out,
        }