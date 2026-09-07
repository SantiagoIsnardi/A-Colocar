"""
Cliente para The Odds API — proveedor dedicado exclusivamente a cuotas,
independiente de la fuente de estadísticas. Free tier: 500 requests/mes.
No comparte IDs con API-Football ni football-data.org, así que el match
se hace por nombre de equipo + fecha (ver the_odds_api_mapper.py).
"""

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import logger

# Sport keys de The Odds API para las competiciones más relevantes
SPORT_KEYS: dict[str, str] = {
    "premier_league": "soccer_epl",
    "la_liga": "soccer_spain_la_liga",
    "bundesliga": "soccer_germany_bundesliga",
    "serie_a": "soccer_italy_serie_a",
    "champions_league": "soccer_uefa_champs_league",
    "mls": "soccer_usa_mls",
    "brasileirao": "soccer_brazil_campeonato",
}


class TheOddsApiClient:

    def __init__(self, api_key: str, base_url: str = "https://api.the-odds-api.com/v4") -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def get_odds(
        self,
        sport_key: str,
        markets: str = "totals",
        regions: str = "eu",
    ) -> list[dict]:
        response = await self._client.get(
            f"/sports/{sport_key}/odds",
            params={
                "apiKey": self._api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": "decimal",
            },
        )
        response.raise_for_status()
        remaining = response.headers.get("x-requests-remaining", "?")
        logger.debug("The Odds API {} | remaining_this_month={}", sport_key, remaining)
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()