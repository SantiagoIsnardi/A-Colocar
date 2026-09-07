from app.services.statistics.calculator import StatisticsCalculator

DEFAULT_LINES: dict[str, list[float]] = {
    "goals":        [0.5, 1.5, 2.5, 3.5, 4.5],
    "corners":      [6.5, 7.5, 8.5, 9.5, 10.5],
    "yellow_cards": [1.5, 2.5, 3.5, 4.5],
    "fouls":        [15.5, 20.5, 25.5, 30.5],
    "shots":        [15.5, 20.5, 25.5],
}

FIELD_MAP = {
    "goals":        "total_goals",
    "corners":      "total_corners",
    "yellow_cards": "total_yellow_cards",
    "fouls":        "total_fouls",
    "shots":        "total_shots",
}


class FrequencyAnalyzer:

    def __init__(self, calculator: StatisticsCalculator) -> None:
        self.calculator = calculator

    async def analyze(
        self,
        team_id: int,
        last_n: int = 10,
        lines: dict[str, list[float]] | None = None,
    ) -> dict:
        """
        Calcula la frecuencia histórica de superar cada línea en cada mercado.
        Resultado clave: % de partidos donde el total superó la línea.
        """
        active_lines = lines or DEFAULT_LINES
        totals = await self.calculator.get_match_totals(team_id, last_n)

        if not totals:
            return {"error": "Sin datos para analizar — ejecutar seed_statistics primero"}

        n = len(totals)
        markets: dict[str, dict] = {}

        for market, line_values in active_lines.items():
            field = FIELD_MAP.get(market)
            if not field:
                continue

            raw_values = [t[field] for t in totals if t.get(field) is not None]
            if not raw_values:
                continue

            sample = len(raw_values)
            market_result: dict[str, dict] = {}

            for line in line_values:
                count_over = sum(1 for v in raw_values if v > line)
                freq = count_over / sample
                market_result[f"over_{line}"] = {
                    "frequency": round(freq, 4),
                    "percentage": round(freq * 100, 1),
                    "count_over": count_over,
                    "count_under_or_equal": sample - count_over,
                    "sample_size": sample,
                    "label": f"Más de {line}",
                }

            markets[market] = market_result

        return {
            "team_id": team_id,
            "matches_analyzed": n,
            "markets": markets,
        }