"""
Closing Line Value: compara la cuota tomada al momento de detectar valor
contra la cuota de cierre del mismo mercado. Es la única prueba objetiva
de ventaja real — si sistemáticamente tomás cuotas mejores que el cierre,
tenés una ventaja genuina sobre el mercado, más allá de si ganaste o
perdiste ese partido puntual.
"""


class CLVTracker:

    @staticmethod
    def calculate_clv(price_taken: float, closing_price: float) -> float:
        """
        CLV positivo = tomaste una cuota mejor que donde cerró el mercado
        (buena señal de timing/valor). CLV negativo = el mercado se movió
        en tu contra después de que apostaste.
        """
        if closing_price <= 0:
            return 0.0
        return round(((price_taken / closing_price) - 1) * 100, 4)

    @staticmethod
    def implied_probability_clv(prob_taken: float, prob_closing: float) -> float:
        """
        CLV expresado en términos de probabilidad implícita en vez de cuota.
        Si tu probabilidad implícita al tomar la apuesta era menor a la de
        cierre, conseguiste una cuota más generosa de lo que el mercado
        terminó valorando ese evento.
        """
        if prob_closing <= 0:
            return 0.0
        return round(((prob_closing / prob_taken) - 1) * 100, 4)