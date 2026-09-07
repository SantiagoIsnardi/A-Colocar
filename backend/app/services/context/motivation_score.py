"""
Score de motivación simplificado. Limitación deliberada del Sprint 6:
el esquema actual no incluye una tabla de posiciones/standings, por lo
que este servicio no puede calcular motivación real basada en objetivos
de temporada (pelea por descenso, pelea por título, etc.).

En su lugar, usa un proxy honesto y explícito: la tendencia de resultados
recientes del equipo (¿está mejorando o empeorando respecto a partidos
anteriores?), documentado como aproximación, no como motivación real.
Si en el futuro se agrega una tabla de standings, este servicio es el
punto de reemplazo natural.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus

MIN_SAMPLE = 6


class MotivationScore:
    """Proxy de motivación basado en tendencia reciente, no en tabla de posiciones."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_trend_score(self, team_id: int, last_n: int = 6) -> dict:
        result = await self.session.execute(
            select(Match)
            .where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                Match.status == MatchStatus.finished,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
            .order_by(Match.match_date.desc())
            .limit(last_n)
        )
        matches = list(result.scalars().all())
        sample = len(matches)

        if sample < MIN_SAMPLE:
            return {
                "trend_score": 0.5,
                "sample_size": sample,
                "sufficient": False,
                "note": "Proxy basado en tendencia — no hay tabla de posiciones en este esquema",
            }

        # Comparar mitad más reciente vs mitad más antigua de la muestra
        half = sample // 2
        recent_half = matches[:half]
        older_half = matches[half:]

        def avg_points(subset: list[Match]) -> float:
            total = 0.0
            for m in subset:
                is_home = m.home_team_id == team_id
                team_goals = m.home_score if is_home else m.away_score
                rival_goals = m.away_score if is_home else m.home_score
                if team_goals > rival_goals:
                    total += 3
                elif team_goals == rival_goals:
                    total += 1
            return total / len(subset)

        recent_avg = avg_points(recent_half)
        older_avg = avg_points(older_half)

        # trend_score > 0.5 = mejorando, < 0.5 = empeorando, 0.5 = estable
        diff = recent_avg - older_avg
        trend_score = 0.5 + max(-0.5, min(0.5, diff / 6.0))

        return {
            "trend_score": round(trend_score, 4),
            "recent_avg_points": round(recent_avg, 2),
            "older_avg_points": round(older_avg, 2),
            "sample_size": sample,
            "sufficient": True,
            "note": "Proxy basado en tendencia — no hay tabla de posiciones en este esquema",
        }