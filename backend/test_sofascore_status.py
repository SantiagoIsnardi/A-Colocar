"""
Prueba puntual: ver qué valores de status.type existen realmente
en los partidos de Sofascore, para corregir el filtro de "próximos".
"""

import ScraperFC as sfc
from collections import Counter

def main():
    sofascore = sfc.Sofascore()
    matches = sofascore.get_match_dicts(year="2026", league="Argentina Liga Profesional")

    statuses = Counter(m.get("status", {}).get("type", "SIN_STATUS") for m in matches)
    print("Valores de status.type encontrados:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")

    # Mostrar un ejemplo de cada tipo
    print("\nEjemplos:")
    seen = set()
    for m in matches:
        st = m.get("status", {}).get("type", "SIN_STATUS")
        if st not in seen:
            seen.add(st)
            home = m.get("homeTeam", {}).get("name", "?")
            away = m.get("awayTeam", {}).get("name", "?")
            print(f"  [{st}] {home} vs {away} | status completo: {m.get('status')}")


if __name__ == "__main__":
    main()