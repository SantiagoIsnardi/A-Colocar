"""
Corrección Dixon-Coles (1997) para el modelo de Poisson de goles.
Corrige la subestimación sistémica de marcadores bajos (0-0, 1-0, 0-1, 1-1)
que produce el Poisson básico al asumir independencia entre goles
del local y del visitante.

Limitación documentada: rho se estima sobre el promedio de liga
disponible en la base de datos, no por par de equipos específico —
con el volumen de datos de un proyecto personal, una estimación
por enfrentamiento individual sería demasiado ruidosa.
"""

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import poisson


class DixonColes:
    RHO_BOUNDS = (-0.3, 0.3)
    DEFAULT_RHO = -0.05  # valor de respaldo si no hay suficientes datos para ajustar

    @staticmethod
    def tau(x: int, y: int, lambda_home: float, lambda_away: float, rho: float) -> float:
        """Factor de corrección aplicado solo a marcadores bajos (0,0), (0,1), (1,0), (1,1)."""
        if x == 0 and y == 0:
            return 1 - (lambda_home * lambda_away * rho)
        if x == 0 and y == 1:
            return 1 + (lambda_home * rho)
        if x == 1 and y == 0:
            return 1 + (lambda_away * rho)
        if x == 1 and y == 1:
            return 1 - rho
        return 1.0

    @classmethod
    def _neg_log_likelihood(
        cls,
        rho: float,
        results: list[tuple[int, int]],
        lambda_home_avg: float,
        lambda_away_avg: float,
    ) -> float:
        log_lik = 0.0
        for home_goals, away_goals in results:
            base_prob = (
                poisson.pmf(home_goals, lambda_home_avg)
                * poisson.pmf(away_goals, lambda_away_avg)
            )
            correction = cls.tau(home_goals, away_goals, lambda_home_avg, lambda_away_avg, rho)
            prob = max(base_prob * correction, 1e-10)  # evita log(0)
            log_lik += np.log(prob)
        return -log_lik

    @classmethod
    def estimate_rho(
        cls,
        results: list[tuple[int, int]],
        lambda_home_avg: float,
        lambda_away_avg: float,
    ) -> float:
        """
        Estima rho por máxima verosimilitud sobre el historial de resultados
        disponible. Si la muestra es chica o la optimización no converge,
        devuelve un valor de respaldo razonable en lugar de fallar.

        Salvaguarda: si el óptimo cae exactamente en el borde del rango
        permitido (RHO_BOUNDS), es señal de que la muestra no alcanza para
        una estimación confiable — el optimizador "se choca contra la pared"
        en vez de encontrar un punto de equilibrio real. En ese caso se
        descarta el resultado y se usa el valor de respaldo.
        """
        if len(results) < 15:
            return cls.DEFAULT_RHO

        try:
            result = minimize_scalar(
                cls._neg_log_likelihood,
                bounds=cls.RHO_BOUNDS,
                method="bounded",
                args=(results, lambda_home_avg, lambda_away_avg),
            )

            if not result.success:
                return cls.DEFAULT_RHO

            estimated_rho = float(result.x)
            lower, upper = cls.RHO_BOUNDS
            edge_tolerance = 1e-3

            # Si el óptimo quedó pegado a cualquiera de los dos bordes,
            # la estimación no es confiable — usar el valor de respaldo.
            if (estimated_rho - lower) < edge_tolerance or (upper - estimated_rho) < edge_tolerance:
                return cls.DEFAULT_RHO

            return estimated_rho

        except Exception:
            return cls.DEFAULT_RHO

    @classmethod
    def apply_correction(
        cls,
        matrix: list[list[float]],
        lambda_home: float,
        lambda_away: float,
        rho: float,
    ) -> list[list[float]]:
        """
        Aplica la corrección tau a las celdas de marcador bajo y renormaliza
        la matriz completa para que la suma de probabilidades siga siendo 1.
        """
        corrected = [row[:] for row in matrix]

        for x in range(min(2, len(matrix))):
            for y in range(min(2, len(matrix[0]))):
                corrected[x][y] = matrix[x][y] * cls.tau(x, y, lambda_home, lambda_away, rho)

        total = sum(sum(row) for row in corrected)
        if total <= 0:
            return matrix  # respaldo: si algo salió mal, devolver matriz sin corregir

        return [[cell / total for cell in row] for row in corrected]