from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus

# Orden de preferencia de fuentes al deduplicar: menor número = mayor prioridad.
# football_data es la fuente oficial para ligas europeas.
_SOURCE_PRIORITY: dict[str, int] = {
    "football_data": 0,
    "sofascore": 1,
    "api_football": 2,
    "manual_test": 99,
}


def _dedup_matches(matches: list[Match]) -> list[Match]:
    """
    Elimina partidos duplicados cross-source de una lista en memoria.

    Un partido está duplicado cuando dos registros comparten el mismo
    (home_team_id, away_team_id, día UTC) pero provienen de distintos
    sources (ej: football_data + sofascore para Premier League).

    Se conserva el registro de mayor prioridad según _SOURCE_PRIORITY
    (menor número = mayor prioridad). En caso de empate de prioridad,
    se conserva el de menor id (primero insertado).
    """
    seen: dict[tuple, Match] = {}
    for m in matches:
        # Clave de partido físico: mismos equipos + mismo día UTC
        day_key = m.match_date.date() if m.match_date else None
        key = (m.home_team_id, m.away_team_id, day_key)

        if key not in seen:
            seen[key] = m
        else:
            existing = seen[key]
            prio_new = _SOURCE_PRIORITY.get(m.source, 50)
            prio_old = _SOURCE_PRIORITY.get(existing.source, 50)
            # Reemplazar si la nueva fuente tiene mayor prioridad (número menor)
            if prio_new < prio_old or (prio_new == prio_old and m.id < existing.id):
                seen[key] = m

    # Restaurar el orden por match_date (el dict puede reordenar)
    return sorted(seen.values(), key=lambda m: m.match_date)


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_id: str, source: str) -> Match | None:
        result = await self.session.execute(
            select(Match).where(Match.external_id == external_id, Match.source == source)
        )
        return result.scalar_one_or_none()

    async def get_by_team_and_date(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date_utc,
        day_window_hours: int = 20,
    ) -> Match | None:
        """
        Busca un partido existente por equipos y fecha (ventana de ±day_window_hours horas).
        Se usa para detectar duplicados cross-source antes de insertar un nuevo registro.
        """
        start = match_date_utc - timedelta(hours=day_window_hours)
        end = match_date_utc + timedelta(hours=day_window_hours)
        result = await self.session.execute(
            select(Match).where(
                Match.home_team_id == home_team_id,
                Match.away_team_id == away_team_id,
                Match.match_date >= start,
                Match.match_date <= end,
            )
        )
        return result.scalars().first()

    async def create(self, match: Match) -> Match:
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
        return match

    async def get_by_team(
        self,
        team_id: int,
        status: MatchStatus | None = None,
        limit: int = 20,
    ) -> list[Match]:
        stmt = (
            select(Match)
            .where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Match.status == status)
        result = await self.session.execute(stmt)
        # Deduplicar también aquí para consistencia en búsqueda por equipo
        return _dedup_matches(list(result.scalars().all()))

    async def get_by_date_range(self, start, end) -> list[Match]:
        """
        Partidos cuya fecha (match_date, en UTC) cae dentro de [start, end).

        Los duplicados cross-source se eliminan en memoria conservando siempre
        el registro de mayor prioridad (football_data > sofascore > api_football).
        Esto resuelve partidos europeos ingresados dos veces (por football_data
        Y por sofascore) sin necesidad de eliminar registros históricos de la BD.
        """
        stmt = (
            select(Match)
            .where(Match.match_date >= start, Match.match_date < end)
            .order_by(Match.match_date.asc())
        )
        result = await self.session.execute(stmt)
        raw = list(result.scalars().all())
        return _dedup_matches(raw)

    async def get_scheduled(self) -> list[Match]:
        """Todos los partidos con status 'scheduled', de cualquier fuente."""
        stmt = select(Match).where(Match.status == MatchStatus.scheduled)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
