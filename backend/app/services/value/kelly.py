"""
Kelly Criterion para el tamaño de stake sugerido, con fracción configurable
para no sugerir apuestas agresivas sobre un modelo todavía no calibrado
formalmente (eso llega en el Sprint 9 — Calibration Engine).
"""


class Kelly:
    DEFAULT_FRACTION = 0.25  # cuarto-Kelly — conservador por diseño
    MAX_STAKE_PCT = 0.05     # tope duro: nunca sugerir más del 5% del bankroll

    @classmethod
    def stake_percentage(
        cls,
        probability_model: float,
        price: float,
        fraction: float = DEFAULT_FRACTION,
    ) -> float:
        """
        Kelly completo: f* = (bp - q) / b
        donde b = price - 1 (cuota neta), p = prob. de ganar, q = 1 - p.

        Se aplica la fracción configurada sobre el Kelly completo, y se
        acota al tope máximo — un edge sobreestimado por error del modelo
        nunca debería traducirse en un stake agresivo.
        """
        b = price - 1.0
        if b <= 0:
            return 0.0

        p = probability_model
        q = 1 - p

        full_kelly = (b * p - q) / b

        if full_kelly <= 0:
            return 0.0

        fractional_kelly = full_kelly * fraction
        return round(min(fractional_kelly, cls.MAX_STAKE_PCT), 4)