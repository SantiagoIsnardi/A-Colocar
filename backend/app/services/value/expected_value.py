"""
Cálculo de valor esperado por unidad apostada, dado el precio decimal
de la cuota y la probabilidad que el modelo asigna al evento.
"""


class ExpectedValue:

    @staticmethod
    def calculate(probability_model: float, price: float) -> float:
        """
        EV por unidad apostada. price es cuota decimal (ej: 1.90).
        profit = price - 1 (ganancia neta si acierta, apostando 1 unidad).
        EV = (p_model * profit) - ((1 - p_model) * 1)
        """
        profit = price - 1.0
        return (probability_model * profit) - ((1 - probability_model) * 1.0)