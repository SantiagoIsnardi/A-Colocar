"""
Extrae el margen real de la casa (vig / overround) de un par de cuotas
over/under, y devuelve la probabilidad implícita "limpia" — sin ese margen.

Sin este paso, comparar la probabilidad del modelo contra la cuota cruda
del mercado siempre parecería mostrar más valor del que realmente existe,
porque la cuota cruda ya tiene el margen de la casa incorporado.
"""


class Devig:

    @staticmethod
    def raw_implied_probability(price: float) -> float:
        """Probabilidad implícita simple, sin descontar margen. price debe ser > 1.0."""
        if price <= 1.0:
            raise ValueError(f"Cuota inválida: {price}")
        return 1 / price

    @classmethod
    def remove_vig(cls, price_over: float, price_under: float) -> dict:
        """
        Método de normalización proporcional (más simple que el método Shin,
        documentado en el esquema como mejora futura si hace falta más precisión).
        """
        raw_over = cls.raw_implied_probability(price_over)
        raw_under = cls.raw_implied_probability(price_under)

        overround = raw_over + raw_under
        margin = overround - 1.0

        if overround <= 0:
            raise ValueError("Overround inválido — cuotas corruptas")

        true_prob_over = raw_over / overround
        true_prob_under = raw_under / overround

        return {
            "true_prob_over": round(true_prob_over, 4),
            "true_prob_under": round(true_prob_under, 4),
            "overround": round(overround, 4),
            "margin": round(margin, 4),
            "margin_percentage": round(margin * 100, 2),
        }