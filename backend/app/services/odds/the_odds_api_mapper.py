"""
Mapea la respuesta de The Odds API a filas planas de cuotas, y resuelve
el partido correspondiente en la base de datos por nombre de equipo
normalizado + proximidad de fecha — The Odds API no comparte IDs con
ninguna otra fuente, así que el cruce es por texto, no por external_id.
"""

import re
from datetime import datetime, timedelta


def _normalize_name(name: str) -> str:
    """'FC Barcelona' -> 'barcelona'. Quita prefijos/sufijos comunes de club."""
    cleaned = re.sub(r"\b(FC|CF|AFC|SC|AC|CD|Club|de|do|the)\b", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", cleaned.lower())


class TheOddsApiMapper:

    @staticmethod
    def extract_odds_rows(event: dict) -> list[dict]:
        """
        Extrae filas planas (bookmaker, market, line, side, price) de un
        evento de The Odds API. Solo procesa mercado 'totals' (goles over/under).
        """
        rows: list[dict] = []

        for bookmaker in event.get("bookmakers", []):
            bookmaker_name = bookmaker.get("title", "unknown")

            for market in bookmaker.get("markets", []):
                if market.get("key") != "totals":
                    continue

                for outcome in market.get("outcomes", []):
                    side = outcome.get("name", "").lower()
                    if side not in ("over", "under"):
                        continue

                    try:
                        line = float(outcome.get("point"))
                        price = float(outcome.get("price"))
                    except (TypeError, ValueError):
                        continue

                    if price <= 1.0:
                        continue

                    rows.append({
                        "bookmaker": bookmaker_name,
                        "market": "goals",
                        "line": line,
                        "side": side,
                        "price": price,
                    })

        return rows

    @staticmethod
    def find_matching_team(event_team_name: str, candidates: list[tuple[int, str]]) -> int | None:
        """
        candidates: lista de (team_id, team_name) de la base de datos.
        Devuelve el team_id cuyo nombre normalizado coincide, o None.
        """
        target = _normalize_name(event_team_name)
        for team_id, team_name in candidates:
            if _normalize_name(team_name) == target:
                return team_id
        return None

    @staticmethod
    def is_same_match_date(event_commence_time: str, match_date: datetime, tolerance_hours: int = 12) -> bool:
        try:
            event_dt = datetime.fromisoformat(event_commence_time.replace("Z", "+00:00"))
        except ValueError:
            return False
        return abs((event_dt - match_date).total_seconds()) <= tolerance_hours * 3600