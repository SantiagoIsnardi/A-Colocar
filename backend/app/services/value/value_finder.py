"""
Cruza la probabilidad del modelo contra la probabilidad implícita del
mercado (ya sin margen de casa) para detectar edges. Es el componente
central del proyecto — convierte predicciones estadísticas en apuestas
de valor identificadas con trazabilidad completa.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.odds import Odds
from app.db.models.prediction import Prediction
from app.db.models.value_bet import ValueBet
from app.db.repositories.odds_repository import OddsRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.value_bet_repository import ValueBetRepository
from app.services.odds.devig import Devig
from app.services.value.expected_value import ExpectedValue
from app.services.value.kelly import Kelly

MIN_EDGE_THRESHOLD = 0.03  # 3% — por debajo se descarta como ruido de redondeo


class ValueFinder:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.prediction_repo = PredictionRepository(session)
        self.odds_repo = OddsRepository(session)
        self.value_bet_repo = ValueBetRepository(session)

    async def find_value_bets(self, match_id: int, market: str = "goals") -> dict:
        """
        Para cada línea con predicción y cuotas disponibles (over y under),
        calcula edge, EV y Kelly. Persiste solo los edges por encima del
        umbral mínimo — el resto se reporta pero no se guarda en la tabla.
        """
        predictions = await self.prediction_repo.get_latest_by_match(match_id=match_id, market=market)
        odds_list = await self.odds_repo.get_latest_by_match(match_id=match_id, market=market)

        if not predictions:
            return {"error": f"Sin predicciones para match {match_id} mercado {market!r}"}
        if not odds_list:
            return {"error": f"Sin cuotas para match {match_id} mercado {market!r}"}

        odds_by_line: dict[float, dict[str, Odds]] = {}
        for o in odds_list:
            line = float(o.line)
            odds_by_line.setdefault(line, {})[o.side] = o

        predictions_by_line: dict[float, Prediction] = {float(p.line): p for p in predictions}

        evaluated = []
        persisted_bets = []

        for line, sides in odds_by_line.items():
            prediction = predictions_by_line.get(line)
            over_odds = sides.get("over")
            under_odds = sides.get("under")

            if not prediction or not over_odds or not under_odds:
                continue

            devig_result = Devig.remove_vig(float(over_odds.price), float(under_odds.price))
            p_model_over = float(prediction.probability_over)
            p_model_under = 1 - p_model_over

            # Evaluar lado OVER
            over_eval = await self._evaluate_side(
                match_id=match_id,
                prediction=prediction,
                odds=over_odds,
                market=market,
                line=line,
                side="over",
                p_model=p_model_over,
                p_implied=devig_result["true_prob_over"],
            )
            evaluated.append(over_eval)
            if over_eval.get("persisted"):
                persisted_bets.append(over_eval)

            # Evaluar lado UNDER
            under_eval = await self._evaluate_side(
                match_id=match_id,
                prediction=prediction,
                odds=under_odds,
                market=market,
                line=line,
                side="under",
                p_model=p_model_under,
                p_implied=devig_result["true_prob_under"],
            )
            evaluated.append(under_eval)
            if under_eval.get("persisted"):
                persisted_bets.append(under_eval)

        if persisted_bets:
            await self.session.commit()

        logger.info(
            "Value Finder | match={} market={} | evaluadas={} | value_bets_detectadas={}",
            match_id, market, len(evaluated), len(persisted_bets),
        )

        return {
            "match_id": match_id,
            "market": market,
            "evaluated_lines": evaluated,
            "value_bets_found": len(persisted_bets),
        }

    async def _evaluate_side(
        self,
        match_id: int,
        prediction: Prediction,
        odds: Odds,
        market: str,
        line: float,
        side: str,
        p_model: float,
        p_implied: float,
    ) -> dict:
        edge = p_model - p_implied
        price = float(odds.price)
        ev = ExpectedValue.calculate(p_model, price)

        result = {
            "line": line,
            "side": side,
            "price": price,
            "probability_model": round(p_model, 4),
            "probability_implied": round(p_implied, 4),
            "edge": round(edge, 4),
            "expected_value": round(ev, 4),
            "persisted": False,
        }

        if edge <= MIN_EDGE_THRESHOLD:
            return result

        # Evitar duplicar la misma value bet si ya existe una abierta
        # equivalente (mismo partido, mercado, línea y lado) — re-analizar
        # un partido no debería acumular filas idénticas en cada corrida.
        existing = await self.value_bet_repo.get_open_equivalent(
            match_id=match_id, market=market, line=line, side=side,
        )

        kelly_stake = Kelly.stake_percentage(p_model, price)

        if existing:
            # Actualizar la fila existente con los valores recalculados
            # en lugar de insertar una nueva — refleja el edge más reciente
            # sin perder la trazabilidad del registro original.
            existing.probability_model = round(p_model, 4)
            existing.probability_implied = round(p_implied, 4)
            existing.edge = round(edge, 4)
            existing.expected_value = round(ev, 4)
            existing.kelly_stake_pct = kelly_stake
            existing.price = price
            existing.prediction_id = prediction.id
            existing.odds_id = odds.id
            await self.session.flush()

            result["persisted"] = True
            result["value_bet_id"] = existing.id
            result["kelly_stake_pct"] = kelly_stake
            result["updated_existing"] = True
            return result

        value_bet = ValueBet(
            match_id=match_id,
            prediction_id=prediction.id,
            odds_id=odds.id,
            market=market,
            line=line,
            side=side,
            probability_model=round(p_model, 4),
            probability_implied=round(p_implied, 4),
            edge=round(edge, 4),
            expected_value=round(ev, 4),
            kelly_stake_pct=kelly_stake,
            price=price,
        )
        self.session.add(value_bet)
        await self.session.flush()

        result["persisted"] = True
        result["value_bet_id"] = value_bet.id
        result["kelly_stake_pct"] = kelly_stake
        result["updated_existing"] = False

        return result