"""
Ponderación temporal por decaimiento exponencial.
Partidos recientes pesan más que partidos antiguos en el cálculo
de fuerza de ataque/defensa y promedios de mercado.
"""

from datetime import datetime, timezone


class TimeDecay:
    DEFAULT_HALF_LIFE_DAYS = 180  # a los 180 días, un partido pesa la mitad

    @classmethod
    def weight(cls, match_date: datetime, half_life_days: int = DEFAULT_HALF_LIFE_DAYS) -> float:
        """Peso decreciente exponencial según antigüedad del partido."""
        now = datetime.now(timezone.utc)
        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=timezone.utc)

        days_ago = max((now - match_date).days, 0)
        return 0.5 ** (days_ago / half_life_days)

    @classmethod
    def weighted_average(cls, values: list[float], weights: list[float]) -> float:
        if not values or sum(weights) == 0:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / sum(weights)