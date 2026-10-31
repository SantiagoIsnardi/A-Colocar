import unicodedata

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.team import Team


def _strip_accents(text: str) -> str:
    """Elimina acentos y tildes para comparación robusta: 'Vélez' -> 'Velez'."""
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_id: str, source: str) -> Team | None:
        result = await self.session.execute(
            select(Team).where(Team.external_id == external_id, Team.source == source)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, team_id: int) -> Team | None:
        result = await self.session.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 10) -> list[Team]:
        """
        Búsqueda insensible a mayúsculas y acentos (unaccent).
        Permite que 'velez' encuentre 'Vélez Sarsfield', 'atletico' encuentre 'Atlético', etc.
        """
        clean = _strip_accents(name.strip())
        try:
            stmt = (
                select(Team)
                .where(
                    or_(
                        func.unaccent(Team.name).ilike(f"%{clean}%"),
                        func.unaccent(func.coalesce(Team.short_name, "")).ilike(f"%{clean}%"),
                    )
                )
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            # Fallback en caso de que unaccent no esté disponible en algún entorno local
            stmt = (
                select(Team)
                .where(
                    or_(
                        Team.name.ilike(f"%{name}%"),
                        Team.short_name.ilike(f"%{name}%"),
                    )
                )
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())

    async def create(self, team: Team) -> Team:
        self.session.add(team)
        await self.session.flush()
        await self.session.refresh(team)
        return team

    async def get_all_id_names(self) -> dict[str, int]:
        """
        Devuelve un diccionario {nombre_equipo: id_db} con todos los equipos.
        """
        stmt = select(Team.name, Team.id)
        result = await self.session.execute(stmt)
        return {name: team_id for name, team_id in result.all()}
