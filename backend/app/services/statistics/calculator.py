from collections import defaultdict

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic


class StatisticsCalculator:
    MIN_SAMPLE = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_finished_match_ids(self, team_id: int, last_n: int) -> list[int]:
        result = await self.session.execute(
            select(Match.id)
            .where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                Match.status == MatchStatus.finished,
            )
            .order_by(Match.match_date.desc())
            .limit(last_n)
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    def _describe(values: list[float]) -> dict | None:
        if not values:
            return None
        arr = np.array(values, dtype=float)
        return {
            "mean": round(float(np.mean(arr)), 2),
            "std": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 2),
            "min": int(np.min(arr)),
            "max": int(np.max(arr)),
            "median": round(float(np.median(arr)), 2),
            "sample_size": len(arr),
        }

    async def get_team_stats(self, team_id: int, last_n: int = 10) -> dict:
        match_ids = await self._get_finished_match_ids(team_id, last_n)

        if len(match_ids) < self.MIN_SAMPLE:
            return {
                "error": f"Muestra insuficiente: {len(match_ids)} partidos (mínimo {self.MIN_SAMPLE})",
                "sample_size": len(match_ids),
            }

        result = await self.session.execute(
            select(Statistic).where(
                Statistic.team_id == team_id,
                Statistic.match_id.in_(match_ids),
            )
        )
        stats = result.scalars().all()

        if not stats:
            return {"error": "Sin estadísticas detalladas — ejecutar seed_statistics primero"}

        return {
            "team_id": team_id,
            "sample_size": len(stats),
            "last_n_requested": last_n,
            "goals_scored": self._describe([s.goals for s in stats]),
            "goals_conceded": self._describe([s.goals_conceded for s in stats]),
            "corners": self._describe([s.corners for s in stats if s.corners is not None]),
            "yellow_cards": self._describe([s.yellow_cards for s in stats if s.yellow_cards is not None]),
            "red_cards": self._describe([s.red_cards for s in stats if s.red_cards is not None]),
            "fouls": self._describe([s.fouls for s in stats if s.fouls is not None]),
            "shots_total": self._describe([s.shots_total for s in stats if s.shots_total is not None]),
            "shots_on_target": self._describe([s.shots_on_target for s in stats if s.shots_on_target is not None]),
        }

    async def get_match_totals(self, team_id: int, last_n: int = 10) -> list[dict]:
        match_ids = await self._get_finished_match_ids(team_id, last_n)
        if not match_ids:
            return []

        result = await self.session.execute(
            select(Statistic).where(Statistic.match_id.in_(match_ids))
        )
        all_stats = result.scalars().all()

        by_match: dict[int, list[Statistic]] = defaultdict(list)
        for s in all_stats:
            by_match[s.match_id].append(s)

        totals = []
        for match_id, rows in by_match.items():
            if len(rows) < 2:
                continue

            def safe_sum(field: str) -> int | None:
                vals = [getattr(r, field) for r in rows if getattr(r, field) is not None]
                return sum(vals) if vals else None

            totals.append({
                "match_id": match_id,
                "total_goals": sum(r.goals for r in rows),
                "total_corners": safe_sum("corners"),
                "total_yellow_cards": safe_sum("yellow_cards"),
                "total_fouls": safe_sum("fouls"),
                "total_shots": safe_sum("shots_total"),
            })

        return totals

    async def get_match_totals_aggregated(self, team_id: int, last_n: int = 10) -> dict:
        totals = await self.get_match_totals(team_id, last_n)
        if not totals:
            return {"error": "Sin datos suficientes"}

        return {
            "team_id": team_id,
            "matches_analyzed": len(totals),
            "total_goals": self._describe([t["total_goals"] for t in totals]),
            "total_corners": self._describe([t["total_corners"] for t in totals if t["total_corners"] is not None]),
            "total_yellow_cards": self._describe([t["total_yellow_cards"] for t in totals if t["total_yellow_cards"] is not None]),
            "total_fouls": self._describe([t["total_fouls"] for t in totals if t["total_fouls"] is not None]),
            "total_shots": self._describe([t["total_shots"] for t in totals if t["total_shots"] is not None]),
        }