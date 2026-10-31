"""
Página de Predicciones: genera y muestra probabilidades por línea para
un partido específico, en los 5 mercados disponibles (goles, corners,
tarjetas amarillas, faltas, tiros).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components import api_client
from components.theme import inject_background
from components.display import render_match_context
from components.match_selector import match_selector

st.set_page_config(page_title="Predicciones", layout="wide")
inject_background()
st.title("Predicciones")

MERCADOS = {
    "goals": "Goles",
    "corners": "Corners",
    "yellow_cards": "Tarjetas Amarillas",
    "fouls": "Faltas",
    "shots": "Tiros",
}

CONFIANZA_TEXTO = {
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
}

STATUS_ESPANOL = {
    "scheduled": "Próximo",
    "SCHEDULED": "Próximo",
    "TIMED": "Próximo",
    "NS": "Próximo",
    "live": "En Vivo",
    "IN_PLAY": "En Vivo",
    "finished": "Finalizado",
    "FINISHED": "Finalizado",
    "FT": "Finalizado",
    "postponed": "Postergado",
    "cancelled": "Cancelado",
}


def _graficar_probabilidades(predicciones: list[dict], mercado_label: str):
    """Gráfico de barras con la probabilidad de superar cada línea."""
    lineas = [p["line"] for p in predicciones]
    porcentajes = [p["percentage"] for p in predicciones]

    fig = go.Figure(data=[
        go.Bar(
            x=[f"Más de {l}" for l in lineas],
            y=porcentajes,
            text=[f"{p}%" for p in porcentajes],
            textposition="outside",
            marker_color="#39D98A",
        )
    ])
    fig.update_layout(
        title=f"Probabilidad por línea — {mercado_label}",
        yaxis_title="Probabilidad (%)",
        yaxis_range=[0, 105],
        showlegend=False,
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#EAF2EC",
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Selector de partido por equipo ───────────────────────────────────────────
match_id = match_selector(key_prefix="pred")

if match_id:
    # Información del partido seleccionado
    match_info = api_client.get_match(match_id)
    es_finalizado = False

    if match_info:
        raw_status = match_info.get("status", "")
        estado_label = STATUS_ESPANOL.get(raw_status, raw_status)
        es_finalizado = raw_status in ("finished", "FINISHED", "FT")

        home = match_info.get("home_team") or f"Equipo #{match_info.get('home_team_id')}"
        away = match_info.get("away_team") or f"Equipo #{match_info.get('away_team_id')}"

        st.caption(
            f"**{home} vs {away}** · {match_info.get('league')} · "
            f"Temporada {match_info.get('season')} · Estado: {estado_label}"
        )

    st.divider()

    mercado = st.selectbox(
        "Mercado",
        options=list(MERCADOS.keys()),
        format_func=lambda x: MERCADOS[x],
    )

    # Cache de predicciones en session_state para evitar que desaparezcan al interactuar
    if "pred_cache" not in st.session_state:
        st.session_state["pred_cache"] = {}

    cache_key = f"{match_id}_{mercado}"

    if es_finalizado:
        st.info("Este partido ya finalizó. Podés consultar la predicción registrada antes del encuentro.")
        if st.button("Consultar predicción", use_container_width=True):
            with st.spinner("Consultando predicción..."):
                res = api_client.get_predictions(match_id, market=mercado)
                if res and "predictions" in res:
                    st.session_state["pred_cache"][cache_key] = res
                else:
                    st.session_state["pred_cache"].pop(cache_key, None)
                    st.warning("No se encontró una predicción previa registrada para este partido.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            generar = st.button("Calcular / Generar predicción", use_container_width=True)
        with col_b:
            consultar = st.button("Consultar predicción existente", use_container_width=True)

        if generar:
            with st.spinner("Calculando predicción con modelos cuantitativos..."):
                if mercado == "goals":
                    res = api_client.generate_goal_predictions(match_id)
                else:
                    res = api_client.generate_market_predictions(match_id, mercado)

                if res and "predictions" in res:
                    st.session_state["pred_cache"][cache_key] = res
                else:
                    st.session_state["pred_cache"].pop(cache_key, None)

        if consultar:
            with st.spinner("Consultando base de datos..."):
                res = api_client.get_predictions(match_id, market=mercado)
                if res and "predictions" in res:
                    res["predictions"] = [
                        {**p, "label": f"Más de {p['line']} {MERCADOS[mercado].lower()}"}
                        for p in res["predictions"]
                    ]
                    st.session_state["pred_cache"][cache_key] = res
                else:
                    st.session_state["pred_cache"].pop(cache_key, None)
                    st.warning("No hay una predicción guardada para este mercado. Hacé clic en 'Calcular / Generar predicción'.")

    # Renderizar resultado si existe en el cache de la sesión
    resultado = st.session_state["pred_cache"].get(cache_key)

    if resultado and "predictions" in resultado and resultado["predictions"]:
        st.divider()

        confianza = resultado.get("confidence_level", "low")
        muestra = resultado.get("sample_size", "?")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nivel de confianza", CONFIANZA_TEXTO.get(confianza, confianza))
        with col2:
            st.metric("Tamaño de muestra", muestra)
        with col3:
            st.metric("Modelo", resultado.get("model_version", "—"))

        if confianza == "low":
            st.warning(
                "Confianza baja: la muestra histórica disponible para uno o ambos equipos "
                "es chica. Interpretá estos números con cautela."
            )

        _graficar_probabilidades(resultado["predictions"], MERCADOS[mercado])

        df = pd.DataFrame(resultado["predictions"])
        df = df.rename(columns={"line": "Línea", "percentage": "Probabilidad (%)"})
        st.dataframe(
            df[["Línea", "Probabilidad (%)"]],
            use_container_width=True,
            hide_index=True,
        )

        if "context" in resultado:
            with st.expander("Ver análisis de contexto (forma, H2H, árbitro, motivación)"):
                render_match_context(resultado["context"])
