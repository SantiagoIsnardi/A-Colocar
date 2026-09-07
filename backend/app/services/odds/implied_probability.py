"""
Conversión de cuota decimal a probabilidad implícita, con y sin margen
descontado. Punto único de conversión usado por el resto del sistema
de valor (Sprint 8).
"""

from app.services.odds.devig import Devig


class ImpliedProbability:

    @staticmethod
    def from_price(price: float) -> float:
        """Probabilidad implícita cruda de una única cuota."""
        return Devig.raw_implied_probability(price)

    @staticmethod
    def clean_pair(price_over: float, price_under: float) -> dict:
        """Probabilidad implícita limpia (sin margen) para un par over/under."""
        return Devig.remove_vig(price_over, price_under)