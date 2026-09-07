"""
Prueba puntual: listar TODOS los nombres de estadísticas disponibles
en un partido de Sofascore, para saber exactamente cómo se llaman
corners, tarjetas amarillas/rojas y faltas.
"""

import ScraperFC as sfc

def main():
    sofascore = sfc.Sofascore()
    match_id = 11937434  # Racing vs Estudiantes, el mismo de ayer

    stats = sofascore.scrape_team_match_stats(match_id)

    print("Todos los nombres de estadísticas disponibles:")
    print("=" * 60)
    for name in stats['name'].tolist():
        print(name)

    print("\n\nBuscando específicamente corners/cards/fouls:")
    print("=" * 60)
    keywords = ['corner', 'card', 'foul', 'yellow', 'red']
    for _, row in stats.iterrows():
        if any(kw in row['name'].lower() for kw in keywords):
            print(f"{row['name']}: home={row['home']} away={row['away']}")


if __name__ == "__main__":
    main()