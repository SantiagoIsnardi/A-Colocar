"""
Brier Score: diferencia cuadrática entre la probabilidad predicha y el
resultado real observado (0 o 1). Cuanto más bajo, mejor calibrado está
el modelo. Un modelo que dice "70% de probabilidad" y acierta el 70% de
las veces en el largo plazo tiene mejor Brier Score que uno que dice
"70%" y acierta solo el 40%, aunque ambos hayan "acertado" este partido.
"""


class BrierScore:

    @staticmethod
    def calculate(predicted_probability: float, actual_outcome: bool) -> float:
        """
        predicted_probability: probabilidad que el modelo asignó al evento (0-1).
        actual_outcome: True si el evento ocurrió, False si no.
        """
        outcome_value = 1.0 if actual_outcome else 0.0
        return round((predicted_probability - outcome_value) ** 2, 5)

    @staticmethod
    def average(scores: list[float]) -> float:
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 5)