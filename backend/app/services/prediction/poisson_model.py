from scipy.stats import poisson

from app.services.prediction.dixon_coles import DixonColes


class PoissonModel:
    """
    Modelo de Poisson para goles, con corrección Dixon-Coles opcional
    para compensar la subestimación de marcadores bajos.
    """

    MAX_GOALS = 10

    @classmethod
    def score_matrix(
        cls,
        lambda_home: float,
        lambda_away: float,
        rho: float | None = None,
    ) -> list[list[float]]:
        """
        Matriz de probabilidad para cada marcador exacto (home_goals, away_goals).
        Si se provee rho, aplica la corrección Dixon-Coles sobre marcadores bajos.
        """
        home_probs = [poisson.pmf(i, lambda_home) for i in range(cls.MAX_GOALS + 1)]
        away_probs = [poisson.pmf(j, lambda_away) for j in range(cls.MAX_GOALS + 1)]

        matrix = [
            [home_probs[i] * away_probs[j] for j in range(cls.MAX_GOALS + 1)]
            for i in range(cls.MAX_GOALS + 1)
        ]

        if rho is not None:
            matrix = DixonColes.apply_correction(matrix, lambda_home, lambda_away, rho)

        return matrix

    @classmethod
    def prob_over_total_goals(cls, matrix: list[list[float]], line: float) -> float:
        total = 0.0
        for i in range(cls.MAX_GOALS + 1):
            for j in range(cls.MAX_GOALS + 1):
                if (i + j) > line:
                    total += matrix[i][j]
        return min(total, 1.0)

    @classmethod
    def total_goals_distribution(cls, matrix: list[list[float]]) -> dict[int, float]:
        dist: dict[int, float] = {}
        for i in range(cls.MAX_GOALS + 1):
            for j in range(cls.MAX_GOALS + 1):
                total = i + j
                dist[total] = dist.get(total, 0.0) + matrix[i][j]
        return dist