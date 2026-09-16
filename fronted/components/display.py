"""
Renderizado genérico de resultados del backend (dicts anidados) como
tarjetas y métricas, en vez de volcar el JSON crudo con st.json().
"""

import streamlit as st

# Campos técnicos que no le sirven al usuario final, se ocultan siempre.
_HIDDEN_KEYS = {"model_version", "computed_at"}

# Traducciones. Si un campo no está acá, se muestra igual (capitalizado),
# pero conviene ir completando esta lista a medida que aparezcan nuevos.
_LABELS = {
    "probability_over": "Probabilidad",
    "percentage": "Porcentaje",
    "confidence_level": "Confianza",
    "sample_size": "Muestra",
    "line": "Línea",
    "lambda_home": "λ local",
    "lambda_away": "λ visitante",
    "home_attack_multiplier": "Mult. ataque local",
    "away_attack_multiplier": "Mult. ataque visitante",
    "match_id": "Partido",
    "market": "Mercado",
    # Forma
    "form_score": "Forma",
    "avg_points_per_match": "Puntos prom./partido",
    "sufficient": "Muestra suficiente",
    # Head to head
    "home_wins": "Victorias local",
    "draws": "Empates",
    "away_wins": "Victorias visitante",
    "home_win_rate": "% victorias local",
    "avg_home_goals": "Goles prom. local",
    "avg_away_goals": "Goles prom. visitante",
    # Motivación
    "trend_score": "Tendencia",
    "recent_avg_points": "Puntos prom. (reciente)",
    "older_avg_points": "Puntos prom. (anterior)",
    # Árbitro
    "available": "Datos disponibles",
    "referee_name": "Árbitro",
    "avg_yellow_cards_per_match": "Amarillas prom./partido",
    "avg_red_cards_per_match": "Rojas prom./partido",
    "avg_fouls_per_match": "Faltas prom./partido",
    # Contexto general
    "home_form": "Forma local",
    "away_form": "Forma visitante",
    "head_to_head": "Historial entre ambos",
    "referee_profile": "Perfil del árbitro",
    "home_motivation": "Motivación local",
    "away_motivation": "Motivación visitante",
}

# Campos de texto libre (pueden ser largos): se muestran aparte, nunca
# como métrica, para que no se corten.
_TEXT_KEYS = {"reason", "note"}

# Umbral: strings más largos que esto tampoco van a métrica, por las dudas
# aparezca un texto largo en un campo que no anticipamos.
_MAX_METRIC_TEXT = 18


def _label(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " ").capitalize())


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.3f}" if abs(value) < 10 else f"{value:.1f}"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def render_result(data: dict, title: str | None = None) -> None:
    """
    Muestra un dict del backend como tarjetas de métricas + secciones
    expandibles para sub-dicts y tablas para listas de dicts.
    """
    if title:
        st.subheader(title)

    data = {k: v for k, v in data.items() if k not in _HIDDEN_KEYS}

    texts = {
        k: v for k, v in data.items()
        if isinstance(v, str) and (k in _TEXT_KEYS or len(v) > _MAX_METRIC_TEXT)
    }
    scalars = {
        k: v for k, v in data.items()
        if isinstance(v, (int, float, bool)) or (isinstance(v, str) and k not in texts)
    }
    nested_dicts = {k: v for k, v in data.items() if isinstance(v, dict)}
    lists_of_dicts = {
        k: v for k, v in data.items()
        if isinstance(v, list) and v and all(isinstance(item, dict) for item in v)
    }

    if scalars:
        cols = st.columns(min(len(scalars), 4))
        for i, (key, value) in enumerate(scalars.items()):
            with cols[i % len(cols)]:
                st.metric(_label(key), _fmt(value))

    for key, value in texts.items():
        st.caption(f"**{_label(key)}:** {value}")

    for key, items in lists_of_dicts.items():
        cleaned = [{k: v for k, v in item.items() if k not in _HIDDEN_KEYS} for item in items]
        st.markdown(f"**{_label(key)}**")
        st.dataframe(cleaned, use_container_width=True, hide_index=True)

    for key, sub in nested_dicts.items():
        with st.expander(_label(key)):
            render_result(sub)