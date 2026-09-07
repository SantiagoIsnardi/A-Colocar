from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus
from app.services.prediction.time_decay import TimeDecay


class TeamStrengthService:
    """
    Calcula la fuerza de ataque y defensa de un equipo, relativa al promedio
    de goles observado en los datos disponibles, ponderando partidos
    recientes por sobre partidos antiguos (decaimiento exponencial).
    """

    MIN_MATCHES = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def league_averages(self) -> dict[str, float]:
        result = await self.session.execute(
            select(Match.home_score, Match.away_score).where(
                Match.status == MatchStatus.finished,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
        )
        rows = result.fetchall()
        if not rows:
            return {"avg_home_goals": 1.4, "avg_away_goals": 1.1}

        home_goals = [r[0] for r in rows]
        away_goals = [r[1] for r in rows]

        return {
            "avg_home_goals": sum(home_goals) / len(home_goals),
            "avg_away_goals": sum(away_goals) / len(away_goals),
        }

    async def get_all_finished_results(self) -> list[tuple[int, int]]:
        """Resultados (home_score, away_score) de todos los partidos finalizados — usado por Dixon-Coles."""
        result = await self.session.execute(
            select(Match.home_score, Match.away_score).where(
                Match.status == MatchStatus.finished,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
        )
        return [(r[0], r[1]) for r in result.fetchall()]

    async def _home_matches(self, team_id: int) -> list[Match]:
        result = await self.session.execute(
            select(Match).where(
                Match.home_team_id == team_id,
                Match.status == MatchStatus.finished,
                Match.home_score.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def _away_matches(self, team_id: int) -> list[Match]:
        result = await self.session.execute(
            select(Match).where(
                Match.away_team_id == team_id,
                Match.status == MatchStatus.finished,
                Match.away_score.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def get_home_strength(self, team_id: int, league_avg: dict[str, float]) -> dict:
        matches = await self._home_matches(team_id)
        sample = len(matches)

        if sample < self.MIN_MATCHES:
            return {"attack": 1.0, "defense": 1.0, "sample_size": sample, "sufficient": False}

        weights = [TimeDecay.weight(m.match_date) for m in matches]
        scored = [m.home_score for m in matches]
        conceded = [m.away_score for m in matches]

        avg_scored = TimeDecay.weighted_average(scored, weights)
        avg_conceded = TimeDecay.weighted_average(conceded, weights)

        return {
            "attack": avg_scored / league_avg["avg_home_goals"],
            "defense": avg_conceded / league_avg["avg_away_goals"],
            "sample_size": sample,
            "sufficient": True,
        }

    async def get_away_strength(self, team_id: int, league_avg: dict[str, float]) -> dict:
        matches = await self._away_matches(team_id)
        sample = len(matches)

        if sample < self.MIN_MATCHES:
            return {"attack": 1.0, "defense": 1.0, "sample_size": sample, "sufficient": False}

        weights = [TimeDecay.weight(m.match_date) for m in matches]
        scored = [m.away_score for m in matches]
        conceded = [m.home_score for m in matches]

        avg_scored = TimeDecay.weighted_average(scored, weights)
        avg_conceded = TimeDecay.weighted_average(conceded, weights)

        return {
            "attack": avg_scored / league_avg["avg_away_goals"],
            "defense": avg_conceded / league_avg["avg_home_goals"],
            "sample_size": sample,
            "sufficient": True,
        }