"""
Cliente HTTP centralizado hacia el backend. Todas las páginas de
Streamlit pasan por acá — evita repetir manejo de errores en cada página
y centraliza la URL base del backend.
"""

import httpx
import streamlit as st

try:
    _backend_url = st.secrets["BACKEND_URL"]
except (KeyError, FileNotFoundError):
    _backend_url = "http://localhost:8000"

BASE_URL = _backend_url + "/api/v1"


def _handle_response(response: httpx.Response) -> dict | None:
    """Procesa la respuesta HTTP y muestra un error genérico si algo falla."""
    try:
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        # El "detail" viene del backend y está pensado para mostrarse al
        # usuario (ej: "Partido no encontrado"); si no viene, usamos un
        # mensaje genérico en vez de exponer la excepción cruda.
        detail = None
        if e.response.content:
            try:
                detail = e.response.json().get("detail")
            except ValueError:
                detail = None
        st.error(detail or "El servidor no pudo procesar la solicitud. Intentá de nuevo más tarde.")
        return None


def _get(path: str, params: dict | None = None) -> dict | None:
    """
    GET genérico con manejo de errores centralizado. Devuelve None si
    falla, mostrando un mensaje genérico en la UI en vez de romper la página.
    """
    try:
        response = httpx.get(f"{BASE_URL}{path}", params=params, timeout=15.0)
        return _handle_response(response)
    except httpx.ConnectError:
        st.error("No se pudo conectar con el servidor. Probá de nuevo en unos minutos.")
        return None
    except httpx.TimeoutException:
        st.error("El servidor tardó demasiado en responder. Probá de nuevo.")
        return None
    except Exception:
        st.error("Ocurrió un error inesperado. Probá de nuevo más tarde.")
        return None


def _post(path: str, params: dict | None = None) -> dict | None:
    """POST genérico, mismo manejo de errores que _get."""
    try:
        response = httpx.post(f"{BASE_URL}{path}", params=params, timeout=30.0)
        return _handle_response(response)
    except httpx.ConnectError:
        st.error("No se pudo conectar con el servidor. Probá de nuevo en unos minutos.")
        return None
    except httpx.TimeoutException:
        st.error("El servidor tardó demasiado en responder. Probá de nuevo.")
        return None
    except Exception:
        st.error("Ocurrió un error inesperado. Probá de nuevo más tarde.")
        return None


# ─── Estadísticas ──────────────────────────────────────────────
def get_team_stats(team_id: int, last_n: int = 10) -> dict | None:
    return _get(f"/statistics/teams/{team_id}", params={"last_n": last_n})


def get_team_frequencies(team_id: int, last_n: int = 10) -> dict | None:
    return _get(f"/statistics/teams/{team_id}/frequencies", params={"last_n": last_n})


# ─── Predicciones ──────────────────────────────────────────────
def generate_goal_predictions(match_id: int, use_context: bool = True) -> dict | None:
    return _post(f"/predictions/matches/{match_id}/goals", params={"use_context": use_context})


def generate_market_predictions(match_id: int, market: str) -> dict | None:
    return _post(f"/predictions/matches/{match_id}/markets/{market}")


def get_predictions(match_id: int, market: str = "goals") -> dict | None:
    return _get(f"/predictions/matches/{match_id}", params={"market": market})


# ─── Odds ──────────────────────────────────────────────────────
def get_match_odds(match_id: int, market: str = "goals") -> dict | None:
    return _get(f"/odds/matches/{match_id}", params={"market": market})


# ─── Value Bets ────────────────────────────────────────────────
def get_value_bets(match_id: int) -> dict | None:
    return _get(f"/value-bets/matches/{match_id}")


def get_rankings(limit_per_market: int = 10) -> dict | None:
    return _get("/rankings/markets", params={"limit_per_market": limit_per_market})


# ─── Análisis completo ─────────────────────────────────────────
def start_full_analysis(match_id: int) -> dict | None:
    return _post(f"/analysis/matches/{match_id}")


def get_analysis_status(task_id: str) -> dict | None:
    return _get(f"/analysis/{task_id}")


# ─── Partidos ──────────────────────────────────────────────────
def get_matches_by_date(date: str | None = None) -> dict | None:
    params = {"date": date} if date else None
    return _get("/matches/by-date", params=params)