"""
Forma reciente ponderada por antigüedad. Reutiliza TimeDecay para dar
más peso a los últimos partidos que a los de hace varias fechas.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus
from app.services.prediction.time_decay import TimeDecay

MIN_SAMPLE = 3


class FormCalculator:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _recent_matches(self, team_id: int, last_n: int = 8) -> list[Match]:
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
        return list(result.scalars().all())

    @staticmethod
    def _points(match: Match, team_id: int) -> float:
        is_home = match.home_team_id == team_id
        team_goals = match.home_score if is_home else match.away_score
        rival_goals = match.away_score if is_home else match.home_score

        if team_goals > rival_goals:
            return 3.0
        if team_goals == rival_goals:
            return 1.0
        return 0.0

    async def get_form_score(self, team_id: int, last_n: int = 8) -> dict:
        """
        Devuelve un score de forma entre 0 y 1 (0 = pésima racha, 1 = racha perfecta),
        ponderado por antigüedad. 0.5 representa una forma neutra (~1.5 pts/partido).
        """
        matches = await self._recent_matches(team_id, last_n)
        sample = len(matches)

        if sample < MIN_SAMPLE:
            return {"form_score": 0.5, "sample_size": sample, "sufficient": False}

        weights = [TimeDecay.weight(m.match_date) for m in matches]
        points = [self._points(m, team_id) for m in matches]

        weighted_avg_points = TimeDecay.weighted_average(points, weights)
        form_score = weighted_avg_points / 3.0  # normalizado a [0, 1]

        return {
            "form_score": round(form_score, 4),
            "avg_points_per_match": round(weighted_avg_points, 2),
            "sample_size": sample,
            "sufficient": True,
        }