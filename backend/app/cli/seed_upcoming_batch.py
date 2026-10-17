"""
Uso:
    python -m app.cli.seed_upcoming_batch 2024

Ingesta masiva de próximos partidos para las 8 competiciones soportadas.
Orquesta ambas fuentes (football-data y API-Football) para evitar
duplicación de "source" y minimizar el uso de cuotas.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal

from app.services.football_data.client import COMPETITION_CODES, FootballDataClient
from app.services.football_data.ingestion_service import FootballDataIngestionService

from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.ingestion_service import IngestionService

# Ligas que exclusivamente dependen de API-Football
API_FOOTBALL_LEAGUES = {
    "Argentina": 128,
    "Libertadores": 13,
}

async def main(season: int) -> None:
    setup_logging()
    
    print("\n=== 1. Procesando Europa (football-data.org) ===")
    if settings.football_data_api_key:
        fd_client = FootballDataClient(
            api_key=settings.football_data_api_key, 
            base_url=settings.football_data_base_url
        )
        try:
            async with AsyncSessionLocal() as session:
                fd_service = FootballDataIngestionService(session, fd_client)
                for name, code in COMPETITION_CODES.items():
                    print(f"Buscando próximos partidos para {name}...")
                    try:
                        # status="SCHEDULED" trae lo próximo sin importar la temporada exacta
                        res = await fd_service.ingest_competition_matches(
                            competition_code=code, 
                            status="SCHEDULED"
                        )
                        print(f"  -> Creados: {res.get('matches_created', 0)} | Omitidos: {res.get('matches_skipped', 0)}")
                    except Exception as e:
                        print(f"  -> Error: {e}")
                    
                    # Pausa de 7s para respetar el límite gratuito de 10 requests/minuto
                    await asyncio.sleep(7)
        finally:
            await fd_client.close()
    else:
        print("Saltando football-data (Sin API KEY)")

    print("\n=== 2. Procesando Sudamérica (API-Football) ===")
    if settings.api_football_key:
        af_client = APIFootballClient(
            api_key=settings.api_football_key, 
            base_url=settings.api_football_base_url
        )
        try:
            async with AsyncSessionLocal() as session:
                af_service = IngestionService(session, af_client)
                for name, league_id in API_FOOTBALL_LEAGUES.items():
                    print(f"Buscando NEXT 15 para {name} (ID: {league_id})...")
                    try:
                        # Gasta solo 1 request por liga
                        res = await af_service.ingest_upcoming_by_league(
                            league_id=league_id, 
                            season=season,
                            next_n=15
                        )
                        print(f"  -> Creados: {res['fixtures_created']} | Omitidos: {res['fixtures_skipped']}")
                    except Exception as e:
                        print(f"  -> Error: {e}")
                    await asyncio.sleep(2)
        finally:
            await af_client.close()
    else:
        print("Saltando API-Football (Sin API KEY)")

    print("\n=== LOTE COMPLETADO ===")

if __name__ == "__main__":
    _season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    asyncio.run(main(_season))