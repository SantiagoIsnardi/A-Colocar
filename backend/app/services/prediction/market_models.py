"""
Generaliza el modelo de tasa-Poisson a mercados que no son goles pero
se comportan de forma similar: eventos discretos por partido con una
tasa promedio (corners, tarjetas amarillas, faltas, tiros).

Simplificación deliberada frente a goles: acá se usa un único lambda
combinado (total esperado del partido, ambos equipos) en lugar de un
lambda separado por equipo con ataque/defensa cruzados. La corrección
Dixon-Coles no aplica a estos mercados — fue diseñada específicamente
para la correlación entre goles de local y visitante en fútbol, no
generaliza a corners o tarjetas.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from scipy.stats import poisson

from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic
from app.services.prediction.time_decay import TimeDecay

STAT_FIELD_MAP: dict[str, str] = {
    "corners": "corners",
    "yellow_cards": "yellow_cards",
    "fouls": "fouls",
    "shots": "shots_total",
}

MIN_SAMPLE = 5


class MarketPredictor:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_team_match_totals(self, team_id: int, field: str, last_n: int = 15) -> list[tuple[float, float]]:
        """
        Devuelve (valor_total_del_partido, peso_temporal) para los últimos N
        partidos finalizados del equipo, donde valor_total es la suma de
        ambos equipos para esa métrica en ese partido.
        """
        stat_column = getattr(Statistic, field)

        result = await self.session.execute(
            select(Match.id, Match.match_date)
            .where(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
                Match.status == MatchStatus.finished,
            )
            .order_by(Match.match_date.desc())
            .limit(last_n)
        )
        matches = result.fetchall()
        if not matches:
            return []

        match_dates = {m.id: m.match_date for m in matches}
        match_ids = list(match_dates.keys())

        stats_result = await self.session.execute(
            select(Statistic.match_id, stat_column).where(
                Statistic.match_id.in_(match_ids),
                stat_column.is_not(None),
            )
        )
        rows = stats_result.fetchall()

        totals_by_match: dict[int, float] = {}
        for match_id, value in rows:
            totals_by_match[match_id] = totals_by_match.get(match_id, 0) + value

        out = []
        for match_id, total in totals_by_match.items():
            weight = TimeDecay.weight(match_dates[match_id])
            out.append((total, weight))

        return out

    async def predict_market(
        self,
        team_id: int,
        market: str,
        lines: list[float],
        last_n: int = 15,
    ) -> dict:
        field = STAT_FIELD_MAP.get(market)
        if not field:
            return {"error": f"Mercado desconocido: {market!r}"}

        data = await self._get_team_match_totals(team_id, field, last_n)

        if len(data) < MIN_SAMPLE:
            return {
                "error": f"Muestra insuficiente: {len(data)} partidos (mínimo {MIN_SAMPLE})",
                "sample_size": len(data),
            }

        values = [d[0] for d in data]
        weights = [d[1] for d in data]
        lambda_total = TimeDecay.weighted_average(values, weights)
        lambda_total = max(lambda_total, 0.1)  # sanidad — evita lambda 0

        predictions_out = []
        for line in lines:
            # P(total > line) = 1 - P(total <= floor(line)), vía CDF de Poisson
            prob_over = 1 - poisson.cdf(int(line), lambda_total)
            prob_over = max(0.0, min(prob_over, 1.0))

            predictions_out.append({
                "line": line,
                "label": f"Más de {line} {market}",
                "probability_over": round(float(prob_over), 4),
                "percentage": round(float(prob_over) * 100, 1),
            })

        confidence = "high" if len(data) >= 20 else "medium" if len(data) >= 10 else "low"

        return {
            "team_id": team_id,
            "market": market,
            "lambda_total": round(lambda_total, 4),
            "sample_size": len(data),
            "confidence_level": confidence,
            "predictions": predictions_out,
        }