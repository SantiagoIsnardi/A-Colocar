"""
Perfil del árbitro asignado: tarjetas promedio por partido y tolerancia
a faltas, cuando la fuente de datos reporta el nombre del árbitro y hay
estadísticas asociadas a esos partidos.

Limitación documentada: los datos de árbitro son el campo menos confiable
o directamente ausente en APIs deportivas de nivel gratuito. Este servicio
debe tratarse como mejora no bloqueante — si no hay datos suficientes,
devuelve un factor neutro en lugar de fallar el análisis completo.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic

MIN_SAMPLE = 5


class RefereeAnalyzer:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_referee_profile(self, referee_name: str | None) -> dict:
        if not referee_name:
            return {"available": False, "reason": "Árbitro no asignado o desconocido"}

        result = await self.session.execute(
            select(Match.id).where(
                Match.referee == referee_name,
                Match.status == MatchStatus.finished,
            )
        )
        match_ids = [row[0] for row in result.fetchall()]

        if len(match_ids) < MIN_SAMPLE:
            return {
                "available": False,
                "reason": f"Muestra insuficiente para {referee_name!r}: {len(match_ids)} partidos",
            }

        stats_result = await self.session.execute(
            select(Statistic.yellow_cards, Statistic.red_cards, Statistic.fouls).where(
                Statistic.match_id.in_(match_ids),
                Statistic.yellow_cards.is_not(None),
            )
        )
        rows = stats_result.fetchall()

        if not rows:
            return {"available": False, "reason": "Sin estadísticas de tarjetas para este árbitro"}

        # Sumar por partido (cada fila es un equipo, dos filas por partido)
        total_yellow = sum(r[0] for r in rows if r[0] is not None)
        total_red = sum(r[1] for r in rows if r[1] is not None)
        total_fouls = sum(r[2] for r in rows if r[2] is not None)
        matches_with_stats = len(match_ids)

        return {
            "available": True,
            "referee_name": referee_name,
            "sample_size": matches_with_stats,
            "avg_yellow_cards_per_match": round(total_yellow / matches_with_stats, 2),
            "avg_red_cards_per_match": round(total_red / matches_with_stats, 2),
            "avg_fouls_per_match": round(total_fouls / matches_with_stats, 2),
        }