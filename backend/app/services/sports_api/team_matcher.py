"""
Resuelve el external_id de API-Football para un equipo que ya existe en
la base con source='football_data', cruzando por nombre normalizado.
Necesario porque football-data.org y API-Football no comparten IDs.
"""

import re

from app.core.cache import cache
from app.services.sports_api.client import APIFootballClient


def _normalize_name(name: str) -> str:
    cleaned = re.sub(r"\b(FC|CF|AFC|SC|AC|CD|Club|de|do|the)\b", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", cleaned.lower())


class TeamMatcher:

    def __init__(self, client: APIFootballClient) -> None:
        self.client = client

    async def find_api_football_id(self, team_name: str) -> int | None:
        """
        Busca el equipo por nombre en API-Football y devuelve su external_id
        si el nombre normalizado coincide razonablemente. Cachea resultados
        para no quemar cuota de requests en cruces repetidos.
        """
        cache_key = f"team_match:{_normalize_name(team_name)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.client.search_teams(team_name)
        candidates = result.get("response", [])

        if not candidates:
            cache.set(cache_key, None, ttl=3600)
            return None

        target = _normalize_name(team_name)
        for candidate in candidates:
            api_team = candidate.get("team", {})
            if _normalize_name(api_team.get("name", "")) == target:
                team_id = int(api_team["id"])
                cache.set(cache_key, team_id, ttl=86400)  # 24hs — el mapeo no cambia
                return team_id

        # Sin coincidencia exacta, usar el primer resultado como mejor esfuerzo
        best_guess = int(candidates[0]["team"]["id"])
        cache.set(cache_key, best_guess, ttl=86400)
        return best_guess