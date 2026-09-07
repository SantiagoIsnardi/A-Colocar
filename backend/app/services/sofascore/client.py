"""
Cliente para Sofascore vía ScraperFC. A diferencia de los clientes HTTP
directos (API-Football, football-data.org), este envuelve una librería
que usa Selenium + Chrome real para scrapear — cada llamada es más lenta
(varios segundos) porque abre/cierra un navegador, pero no tiene límite
diario de requests ni restricción de temporada.

Requiere: pip install ScraperFC, y Google Chrome instalado en el sistema.
"""

import ScraperFC as sfc

from app.core.logging import logger


class SofascoreClient:

    def __init__(self) -> None:
        self._client = sfc.Sofascore()

    def get_valid_seasons(self, league: str) -> dict[str, int]:
        return self._client.get_valid_seasons(league)

    def get_match_dicts(self, year: str, league: str) -> list[dict]:
        matches = self._client.get_match_dicts(year=year, league=league)
        logger.debug("Sofascore | liga={} temporada={} | partidos={}", league, year, len(matches))
        return matches

    def get_team_match_stats(self, match_id: int):
        return self._client.scrape_team_match_stats(match_id)

    def get_match_shots(self, match_id: int):
        return self._client.scrape_match_shots(match_id)