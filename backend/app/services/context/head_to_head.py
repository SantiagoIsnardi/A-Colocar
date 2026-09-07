"""
Head-to-head específico por sede: rendimiento histórico de un equipo
jugando de local contra un rival específico, no el H2H general sin
distinguir sede.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus

MIN_SAMPLE = 3


class HeadToHeadService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_home_vs_away_history(
        self,
        home_team_id: int,
        away_team_id: int,
        last_n: int = 10,
    ) -> dict:
        """
        Historial de enfrentamientos donde home_team_id jugó de local
        contra away_team_id específicamente en esa sede.
        """
        result = await self.session.execute(
            select(Match)
            .where(
                Match.home_team_id == home_team_id,
                Match.away_team_id == away_team_id,
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
            return {"sample_size": sample, "sufficient": False}

        home_wins = sum(1 for m in matches if m.home_score > m.away_score)
        draws = sum(1 for m in matches if m.home_score == m.away_score)
        away_wins = sum(1 for m in matches if m.home_score < m.away_score)

        avg_home_goals = sum(m.home_score for m in matches) / sample
        avg_away_goals = sum(m.away_score for m in matches) / sample

        return {
            "sample_size": sample,
            "sufficient": True,
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round(home_wins / sample, 3),
            "avg_home_goals": round(avg_home_goals, 2),
            "avg_away_goals": round(avg_away_goals, 2),
        }