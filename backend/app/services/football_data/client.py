"""
Cliente para football-data.org — cubre las 6 competiciones europeas de la
lista del usuario con temporada actual real: Premier League, La Liga,
Bundesliga, Serie A, Champions League, Brasileirão. Free tier: 10 req/min,
sin restricción de temporada (a diferencia de API-Football).
"""

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import logger

COMPETITION_CODES: dict[str, str] = {
    "premier_league": "PL",
    "la_liga": "PD",
    "bundesliga": "BL1",
    "serie_a": "SA",
    "champions_league": "CL",
    "brasileirao": "BSA",
}


class FootballDataClient:

    def __init__(self, api_key: str, base_url: str = "https://api.football-data.org/v4") -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Auth-Token": api_key},
            timeout=30.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=15),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        remaining = response.headers.get("x-requests-available-minute", "?")
        logger.debug("football-data.org {} | remaining_this_minute={}", path, remaining)
        return response.json()

    async def get_matches(
        self,
        competition_code: str,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        season: int | None = None,
    ) -> dict:
        """
        season: año de inicio de la temporada (ej: 2025 para temporada 2025/26).
        Sin especificar, football-data.org devuelve la temporada actual.
        """
        params: dict = {}
        if status:
            params["status"] = status
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if season:
            params["season"] = season
        return await self._get(f"/competitions/{competition_code}/matches", params=params)

    async def close(self) -> None:
        await self._client.aclose()