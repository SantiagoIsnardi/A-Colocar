"""
Cliente para Sofascore vía ScraperFC. A diferencia de los clientes HTTP
directos (API-Football, football-data.org), este envuelve una librería
que usa Selenium + Chrome real para scrapear — cada llamada es más lenta
(varios segundos) porque abre/cierra un navegador, pero no tiene límite
diario de requests ni restricción de temporada.

Requiere: pip install ScraperFC, y Google Chrome instalado en el sistema.
"""

import ScraperFC as sfc
from ScraperFC.sofascore import API_PREFIX, comps
from ScraperFC.utils import botasaurus_browser_get_json

from app.core.logging import logger


class SofascoreClient:

    def __init__(self) -> None:
        self._client = sfc.Sofascore()

    def get_valid_seasons(self, league: str) -> dict[str, int]:
        return self._client.get_valid_seasons(league)

    def get_match_dicts(self, year: str, league: str) -> list[dict]:
        """
        Partidos YA JUGADOS de una temporada (endpoint events/last/ de
        Sofascore). Para partidos programados/futuros usar
        get_upcoming_match_dicts en su lugar.
        """
        matches = self._client.get_match_dicts(year=year, league=league)
        logger.debug("Sofascore | liga={} temporada={} | partidos_jugados={}", league, year, len(matches))
        return matches

    def get_upcoming_match_dicts(self, year: str, league: str) -> list[dict]:
        """
        Partidos programados (aún no jugados) de una temporada.

        ScraperFC.Sofascore.get_match_dicts() solo pega contra
        events/last/{i} (resultados históricos) — nunca devuelve
        partidos con status "notstarted". No hay método público en la
        librería para events/next/{i}, así que replicamos acá el mismo
        patrón de paginación que usa la librería internamente, pero
        contra el endpoint correcto.
        """
        valid_seasons = self._client.get_valid_seasons(league)
        if year not in valid_seasons:
            raise ValueError(
                f"Temporada '{year}' inválida para '{league}'. "
                f"Válidas: {list(valid_seasons.keys())}"
            )
        season_id = valid_seasons[year]
        tournament_id = comps[league]["SOFASCORE"]

        matches: list[dict] = []
        page = 0
        while True:
            response = botasaurus_browser_get_json(
                f"{API_PREFIX}/unique-tournament/{tournament_id}/season/{season_id}/events/next/{page}"
            )
            if "events" not in response:
                break
            matches += response["events"]
            page += 1

        logger.debug("Sofascore | liga={} temporada={} | partidos_programados={}", league, year, len(matches))
        return matches

    def get_team_match_stats(self, match_id: int):
        return self._client.scrape_team_match_stats(match_id)

    def get_match_shots(self, match_id: int):
        return self._client.scrape_match_shots(match_id)