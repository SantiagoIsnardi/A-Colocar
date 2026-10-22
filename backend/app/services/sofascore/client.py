"""
Cliente para Sofascore.
Usa sesión activa de Chrome con Botasaurus para superar Cloudflare,
y consume el endpoint moderno https://www.sofascore.com/api/v1 (el antiguo
api.sofascore.com devuelve 403 Forbidden por bloqueo de subdominio).
"""

import json
import ScraperFC as sfc
from ScraperFC.sofascore import comps
from botasaurus.browser import browser
from app.core.logging import logger

SOFASCORE_API_PREFIX = "https://www.sofascore.com/api/v1"
sfc.sofascore.API_PREFIX = SOFASCORE_API_PREFIX

STATIC_SEASON_IDS = {
    "Argentina Liga Profesional": {"2026": 87913},
    "England Premier League": {"26/27": 96668},    
    "Germany Bundesliga": {"26/27": 97464},
    "Spain La Liga": {"26/27": 97268},
    "Italy Serie A": {"26/27": 95836},
    "France Ligue 1": {"26/27": 96127},
    "UEFA Champions League": {"26/27": 96518},
    "CONMEBOL Copa Libertadores": {"2026": 87760}
}


@browser(headless=False, block_images_and_css=False, output=None, create_error_logs=False, close_on_crash=True, wait_for_complete_page_load=False)
def _fetch_paginated_events(driver, data):
    tournament_id = data["tournament_id"]
    season_id = data["season_id"]
    endpoint = data["endpoint"]
    
    logger.info("Chrome VISIBLE abierto. Entrando a la portada para validar sesión...")
    driver.get("https://www.sofascore.com")
    driver.sleep(3)  # Tiempo vital para que Cloudflare nos dé la cookie de acceso
    
    matches = []
    page = 0
    while True:
        url = f"{SOFASCORE_API_PREFIX}/unique-tournament/{tournament_id}/season/{season_id}/events/{endpoint}/{page}"
        logger.debug(f"Consultando eventos Sofascore (pág {page}): {url}")
        
        response = None
        # Intentamos primero fetch en la sesión activa (rápido y con cookies válidas)
        try:
            response = driver.run_js(f"return fetch('{url}').then(r => r.json());")
        except Exception:
            pass

        # Si fetch no devolvió dict, navegamos físicamente a la URL
        if not isinstance(response, dict):
            driver.get(url)
            driver.sleep(1.5)
            text = driver.run_js("return document.body.innerText;")
            try:
                response = json.loads(text)
            except Exception:
                logger.error(f"Sofascore devolvió texto no-JSON en pág {page}. Fin de paginación.")
                break

        if not isinstance(response, dict):
            break

        if "error" in response:
            logger.error(f"Sofascore devolvió error en pág {page}: {response['error']}")
            break
            
        if "events" not in response or len(response["events"]) == 0:
            break
            
        matches += response["events"]
        page += 1
        
    return matches


def _botasaurus_single_fetch(url: str) -> dict:
    clean_url = url.replace("https://api.sofascore.com", "https://www.sofascore.com")
    @browser(headless=False, block_images_and_css=False, output=None, create_error_logs=False, close_on_crash=True, wait_for_complete_page_load=False)
    def _fetch(driver, data):
        driver.get("https://www.sofascore.com")
        driver.sleep(3)
        try:
            return driver.run_js(f"return fetch('{clean_url}').then(r => r.json());")
        except Exception:
            driver.get(clean_url)
            driver.sleep(1.5)
            text = driver.run_js("return document.body.innerText;")
            try:
                return json.loads(text)
            except Exception:
                return {}
    return _fetch()

sfc.utils.botasaurus_browser_get_json = _botasaurus_single_fetch


class SofascoreClient:

    def __init__(self) -> None:
        self._client = sfc.Sofascore()

    def get_valid_seasons(self, league: str) -> dict[str, int]:
        if league in STATIC_SEASON_IDS:
            return STATIC_SEASON_IDS[league]
        return {}

    def get_match_dicts(self, year: str, league: str) -> list[dict]:
        valid_seasons = self.get_valid_seasons(league)
        if year not in valid_seasons:
            raise ValueError(f"Temporada '{year}' inválida para '{league}'. Válidas: {list(valid_seasons.keys())}")
        
        matches = _fetch_paginated_events(data={
            "tournament_id": comps[league]["SOFASCORE"],
            "season_id": valid_seasons[year],
            "endpoint": "last"
        })
        
        if matches is None:
            matches = []

        logger.debug("Sofascore | liga={} temporada={} | partidos_jugados={}", league, year, len(matches))
        return matches

    def get_upcoming_match_dicts(self, year: str, league: str) -> list[dict]:
        valid_seasons = self.get_valid_seasons(league)
        if year not in valid_seasons:
            raise ValueError(f"Temporada '{year}' inválida para '{league}'. Válidas: {list(valid_seasons.keys())}")
            
        matches = _fetch_paginated_events(data={
            "tournament_id": comps[league]["SOFASCORE"],
            "season_id": valid_seasons[year],
            "endpoint": "next"
        })
        
        if matches is None:
            matches = []

        logger.debug("Sofascore | liga={} temporada={} | partidos_programados={}", league, year, len(matches))
        return matches

    def get_team_match_stats(self, match_id: int):
        return self._client.scrape_team_match_stats(match_id)

    def get_match_shots(self, match_id: int):
        return self._client.scrape_match_shots(match_id)
