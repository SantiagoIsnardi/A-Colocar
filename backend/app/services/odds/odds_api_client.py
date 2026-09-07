"""
Mapea la respuesta cruda de /odds de API-Football a un formato interno
normalizado: (market, line, side, price, bookmaker). API-Football agrupa
las cuotas por "bet" (tipo de apuesta) con nombres como "Goals Over/Under",
"Cards Over/Under", cada una con values como "Over 2.5" / "Under 2.5".
"""

_BET_NAME_TO_MARKET: dict[str, str] = {
    "Goals Over/Under": "goals",
    "Corners Over/Under": "corners",
    "Cards Over/Under": "yellow_cards",
}


class OddsApiMapper:

    @staticmethod
    def _parse_value_label(label: str) -> tuple[str, float] | None:
        """'Over 2.5' -> ('over', 2.5). 'Under 2.5' -> ('under', 2.5)."""
        parts = label.strip().split()
        if len(parts) != 2:
            return None

        side_raw, line_raw = parts
        side = side_raw.lower()
        if side not in ("over", "under"):
            return None

        try:
            line = float(line_raw)
        except ValueError:
            return None

        return side, line

    @classmethod
    def extract_odds_rows(cls, odds_response: dict) -> list[dict]:
        """
        Devuelve una lista de filas planas:
        {bookmaker, market, line, side, price}
        listas para persistir como registros de Odds.
        """
        rows: list[dict] = []
        response_list = odds_response.get("response", [])

        for fixture_odds in response_list:
            for bookmaker_entry in fixture_odds.get("bookmakers", []):
                bookmaker_name = bookmaker_entry.get("name", "unknown")

                for bet in bookmaker_entry.get("bets", []):
                    bet_name = bet.get("name", "")
                    market = _BET_NAME_TO_MARKET.get(bet_name)
                    if not market:
                        continue

                    for value in bet.get("values", []):
                        label = value.get("value", "")
                        parsed = cls._parse_value_label(label)
                        if not parsed:
                            continue

                        side, line = parsed
                        try:
                            price = float(value.get("odd"))
                        except (TypeError, ValueError):
                            continue

                        if price <= 1.0:
                            continue

                        rows.append({
                            "bookmaker": bookmaker_name,
                            "market": market,
                            "line": line,
                            "side": side,
                            "price": price,
                        })

        return rows