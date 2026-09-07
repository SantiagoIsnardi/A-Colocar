import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.exceptions import ExternalAPIError
from app.core.logging import logger


def _is_retryable(exc: BaseException) -> bool:
    """
    Reintenta errores de red y 5xx (transitorios). NO reintenta 429
    (rate limit) — insistir contra un rate limit ya excedido solo empeora
    la situación; mejor fallar rápido y dejar que la cuota se libere.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


class APIFootballClient:

    def __init__(self, api_key: str, base_url: str = "https://v3.football.api-sports.io") -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"x-apisports-key": api_key},
            timeout=30.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception(_is_retryable),
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params)

        if response.status_code == 429:
            logger.warning("API Football rate limit alcanzado en {}", path)
            raise ExternalAPIError("API-Football: límite de requests alcanzado, intentar más tarde")

        response.raise_for_status()
        data = response.json()
        remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
        logger.debug("API Football {} | remaining={}", path, remaining)
        return data

    async def search_teams(self, name: str) -> dict:
        return await self._get("/teams", params={"search": name})

    async def get_team(self, team_id: int) -> dict:
        return await self._get("/teams", params={"id": team_id})

    async def get_fixtures_by_team(self, team_id: int, season: int, last: int = 20) -> dict:
        return await self._get(
            "/fixtures",
            params={"team": team_id, "season": season, "status": "FT"},
        )

    async def get_fixture_statistics(self, fixture_id: int) -> dict:
        return await self._get("/fixtures/statistics", params={"fixture": fixture_id})

    async def get_fixture_odds(self, fixture_id: int, bookmaker_id: int | None = None) -> dict:
        params: dict = {"fixture": fixture_id}
        if bookmaker_id is not None:
            params["bookmaker"] = bookmaker_id
        return await self._get("/odds", params=params)

    async def get_upcoming_fixtures(self, team_id: int, next_n: int = 5) -> dict:
        from datetime import datetime, timedelta

        today = datetime.utcnow().date()
        to_date = today + timedelta(days=90)

        return await self._get(
            "/fixtures",
            params={
                "team": team_id,
                "from": today.isoformat(),
                "to": to_date.isoformat(),
                "status": "NS",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()