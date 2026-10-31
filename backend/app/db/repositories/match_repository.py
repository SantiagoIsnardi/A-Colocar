import unicodedata
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.match import Match, MatchStatus
from app.db.models.team import Team

# Orden de preferencia de fuentes al deduplicar: menor número = mayor prioridad.
# football_data es la fuente oficial para ligas europeas.
_SOURCE_PRIORITY: dict[str, int] = {
    "football_data": 0,
    "sofascore": 1,
    "api_football": 2,
    "manual_test": 99,
}


def _normalize(name: str) -> str:
    """
    Normaliza un nombre de equipo para comparación fuzzy:
    - Minúsculas
    - Sin acentos (NFD → solo ASCII)
    - Sin espacios extra
    Ejemplo: "FC Augsburg" → "fc augsburg", "Borussia M'gladbach" → "borussia mgladbach"
    """
    name = name.strip().lower()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Eliminar caracteres no alfanuméricos excepto espacios
    name = "".join(c if c.isalnum() or c == " " else "" for c in name)
    return " ".join(name.split())


def _dedup_matches(
    matches: list[Match],
    team_names: dict[int, str] | None = None,
    reverse: bool = False,
) -> list[Match]:
    """
    Elimina partidos duplicados cross-source de una lista en memoria.

    Estrategia de clave (en orden de prioridad):
    1. (home_team_id, away_team_id, día_UTC)  → clave exacta por ID
    2. (home_name_norm, away_name_norm, día_UTC) → clave por nombre normalizado,
       para cuando sofascore y football_data tienen distintos team_ids para el
       mismo equipo real (ej: Bundesliga).

    Se conserva el registro de mayor prioridad según _SOURCE_PRIORITY
    (menor número = mayor prioridad). En empate de prioridad, se conserva
    el de menor id (primero insertado).

    Args:
        matches: lista de Match de la BD.
        team_names: dict {team_id: nombre} para hacer dedup por nombre.
                    Si es None, solo se usa la clave por ID.
    """
    seen_by_id: dict[tuple, Match] = {}
    seen_by_name: dict[tuple, Match] = {}

    def _priority(m: Match) -> int:
        return _SOURCE_PRIORITY.get(m.source, 50)

    def _keep(candidate: Match, existing: Match) -> bool:
        """True si candidate debe reemplazar a existing."""
        p_new = _priority(candidate)
        p_old = _priority(existing)
        return p_new < p_old or (p_new == p_old and candidate.id < existing.id)

    for m in matches:
        day_key = m.match_date.date() if m.match_date else None

        # Clave 1: por team_id exacto
        id_key = (m.home_team_id, m.away_team_id, day_key)
        if id_key not in seen_by_id:
            seen_by_id[id_key] = m
        elif _keep(m, seen_by_id[id_key]):
            seen_by_id[id_key] = m

        # Clave 2: por nombre normalizado (fallback para IDs distintos)
        if team_names:
            home_norm = _normalize(team_names.get(m.home_team_id, ""))
            away_norm = _normalize(team_names.get(m.away_team_id, ""))
            if home_norm and away_norm:
                name_key = (home_norm, away_norm, day_key)
                if name_key not in seen_by_name:
                    seen_by_name[name_key] = m
                elif _keep(m, seen_by_name[name_key]):
                    seen_by_name[name_key] = m

    # Unir ambos conjuntos: si un partido ganó en seen_by_name, usarlo
    # (puede tener mejor prioridad que el que quedó en seen_by_id)
    final: dict[int, Match] = {}
    for m in seen_by_id.values():
        final[m.id] = m
    if team_names:
        for m in seen_by_name.values():
            # El partido del seen_by_name "gana" si su prioridad es mayor que
            # cualquier partido con el mismo nombre ya en final
            final[m.id] = m

    # Ahora eliminar pares que comparten nombre (el de mayor prioridad gana)
    if team_names:
        name_winner: dict[tuple, Match] = {}
        for m in final.values():
            day_key = m.match_date.date() if m.match_date else None
            home_norm = _normalize(team_names.get(m.home_team_id, ""))
            away_norm = _normalize(team_names.get(m.away_team_id, ""))
            if not home_norm or not away_norm:
                continue
            name_key = (home_norm, away_norm, day_key)
            if name_key not in name_winner:
                name_winner[name_key] = m
            elif _keep(m, name_winner[name_key]):
                name_winner[name_key] = m

        # Construir set de IDs ganadores
        winner_ids = {m.id for m in name_winner.values()}
        result = [m for m in final.values() if m.id in winner_ids]
    else:
        result = list(final.values())

    return sorted(result, key=lambda m: m.match_date, reverse=reverse)


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _load_team_names(self, match_list: list[Match]) -> dict[int, str]:
        """Carga nombres de equipos para una lista de partidos (para dedup por nombre)."""
        team_ids = {m.home_team_id for m in match_list} | {m.away_team_id for m in match_list}
        if not team_ids:
            return {}
        result = await self.session.execute(
            select(Team.id, Team.name).where(Team.id.in_(team_ids))
        )
        return dict(result.all())

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
        limit: int = 30,
    ) -> list[Match]:
        # Unificar IDs de equipo si existe duplicado por fuente en la tabla teams (ej: FC Augsburg)
        team = await self.session.get(Team, team_id)
        team_ids = {team_id}
        if team:
            try:
                norm_target = _normalize(team.name)
                all_teams_res = await self.session.execute(select(Team.id, Team.name))
                for t_id, t_name in all_teams_res.all():
                    if _normalize(t_name) == norm_target:
                        team_ids.add(t_id)
            except Exception:
                pass

        stmt = (
            select(Match)
            .where(or_(Match.home_team_id.in_(team_ids), Match.away_team_id.in_(team_ids)))
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Match.status == status)
        result = await self.session.execute(stmt)
        raw = list(result.scalars().all())
        team_names = await self._load_team_names(raw)
        return _dedup_matches(raw, team_names, reverse=True)

    async def get_by_date_range(self, start, end) -> list[Match]:
        """
        Partidos cuya fecha (match_date, en UTC) cae dentro de [start, end).

        Los duplicados cross-source se eliminan en memoria conservando siempre
        el registro de mayor prioridad (football_data > sofascore > api_football).
        Funciona incluso cuando sofascore y football_data usan distintos team_ids
        para el mismo equipo real (ej: equipos de Bundesliga), usando nombre
        normalizado como clave de fallback.
        """
        stmt = (
            select(Match)
            .where(Match.match_date >= start, Match.match_date < end)
            .order_by(Match.match_date.asc())
        )
        result = await self.session.execute(stmt)
        raw = list(result.scalars().all())
        team_names = await self._load_team_names(raw)
        return _dedup_matches(raw, team_names)

    async def get_scheduled(self) -> list[Match]:
        """Todos los partidos con status 'scheduled', de cualquier fuente."""
        stmt = select(Match).where(Match.status == MatchStatus.scheduled)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
