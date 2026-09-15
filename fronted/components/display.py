"""
Renderizado genérico de resultados del backend (dicts anidados) como
tarjetas y métricas, en vez de volcar el JSON crudo con st.json().
"""

import streamlit as st

_LABELS = {
    "probability_over": "Probabilidad",
    "percentage": "Porcentaje",
    "confidence_level": "Confianza",
    "sample_size": "Muestra",
    "model_version": "Versión modelo",
    "lambda_home": "λ local",
    "lambda_away": "λ visitante",
    "line": "Línea",
    "form_score": "Forma",
    "trend_score": "Tendencia",
    "home_attack_multiplier": "Mult. ataque local",
    "away_attack_multiplier": "Mult. ataque visitante",
}


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

    scalars = {k: v for k, v in data.items() if isinstance(v, (int, float, str, bool)) and v is not None}
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

    for key, items in lists_of_dicts.items():
        st.markdown(f"**{_label(key)}**")
        st.dataframe(items, use_container_width=True, hide_index=True)

    for key, sub in nested_dicts.items():
        with st.expander(_label(key)):
            render_result(sub)