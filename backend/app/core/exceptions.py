"""
Jerarquía de excepciones propia de la aplicación. Todos los servicios
deberían lanzar estas excepciones en vez de errores genéricos de Python,
para que la capa de API pueda traducirlas a respuestas HTTP consistentes.
"""


class AppException(Exception):
    """Excepción base de la aplicación."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DataNotFoundError(AppException):
    """El recurso solicitado no existe."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class InsufficientDataError(AppException):
    """Hay datos, pero no alcanzan el mínimo requerido para un cálculo confiable."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class ExternalAPIError(AppException):
    """Fallo al comunicarse con una API externa (API-Football, football-data.org, The Odds API)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)


class InvalidRequestError(AppException):
    """El request del cliente es inválido (parámetros incorrectos, mercado desconocido, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class AnalysisInProgressError(AppException):
    """Ya hay un análisis en curso para este partido — evita duplicar trabajo en background."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)