"""
Script de PRUEBA AISLADA — no toca la base de datos ni el pipeline existente.
Objetivo: ver la estructura real de datos que devuelve ScraperFC/Sofascore
para un partido específico, antes de decidir si integrarlo al proyecto.

Uso:
    python test_scraperfc.py

Requiere:
    pip install ScraperFC
"""

import ScraperFC as sfc

def main():
    sofascore = sfc.Sofascore()

    print("=" * 60)
    print("PASO 1: Verificando estructura de comps.yaml (ligas disponibles)")
    print("=" * 60)

    league = "Argentina Liga Profesional"
    year = "2024"

    print(f"\nPASO 2: Buscando temporadas válidas para '{league}'...")
    try:
        valid_seasons = sofascore.get_valid_seasons(league)
        print(f"Temporadas encontradas: {valid_seasons}")
    except Exception as e:
        print(f"ERROR al buscar temporadas: {e}")
        print("Puede que el nombre de liga no coincida exactamente. Revisar comps.yaml del paquete.")
        return

    print(f"\nPASO 3: Trayendo partidos de {league} temporada {year}...")
    try:
        matches = sofascore.get_match_dicts(year=year, league=league)
        print(f"Total de partidos encontrados: {len(matches)}")
        if matches:
            print("\nPrimer partido (estructura completa):")
            print(matches[0])
    except Exception as e:
        print(f"ERROR al traer partidos: {e}")
        return

    if not matches:
        print("No se encontraron partidos, deteniendo prueba.")
        return

    sample_match = matches[0]
    match_id = sample_match.get("id")
    print(f"\nPASO 4: Trayendo estadísticas de equipo para match_id={match_id}...")

    try:
        team_stats = sofascore.scrape_team_match_stats(match_id)
        print("\nEstadísticas de equipo (DataFrame):")
        print(team_stats)
        print("\nColumnas disponibles:")
        print(list(team_stats.columns))
    except Exception as e:
        print(f"ERROR al traer estadísticas de equipo: {e}")

    print(f"\nPASO 5: Trayendo tiros (shots) para match_id={match_id}...")
    try:
        shots = sofascore.scrape_match_shots(match_id)
        print("\nTiros (DataFrame):")
        print(shots.head(10))
        print(f"\nTotal de tiros registrados: {len(shots)}")
    except Exception as e:
        print(f"ERROR al traer tiros: {e}")


if __name__ == "__main__":
    main()