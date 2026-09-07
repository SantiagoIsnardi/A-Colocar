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

st.set_page_config(page_title="Predicciones", page_icon="📊", layout="wide")
st.title("📊 Predicciones")

MERCADOS = {
    "goals": "Goles",
    "corners": "Corners",
    "yellow_cards": "Tarjetas Amarillas",
    "fouls": "Faltas",
    "shots": "Tiros",
}

CONFIANZA_COLOR = {
    "high": "🟢",
    "medium": "🟡",
    "low": "🔴",
}

CONFIANZA_TEXTO = {
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
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
            marker_color="#1f77b4",
        )
    ])
    fig.update_layout(
        title=f"Probabilidad por línea — {mercado_label}",
        yaxis_title="Probabilidad (%)",
        yaxis_range=[0, 105],
        showlegend=False,
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


match_id = st.number_input("Match ID", min_value=1, step=1, value=None)

if match_id:
    mercado = st.selectbox(
        "Mercado",
        options=list(MERCADOS.keys()),
        format_func=lambda x: MERCADOS[x],
    )

    col_a, col_b = st.columns(2)
    with col_a:
        generar = st.button("🔄 Generar nueva predicción", use_container_width=True)
    with col_b:
        consultar = st.button("📋 Consultar predicción existente", use_container_width=True)

    resultado = None

    if generar:
        with st.spinner("Calculando predicción..."):
            if mercado == "goals":
                resultado = api_client.generate_goal_predictions(match_id)
            else:
                resultado = api_client.generate_market_predictions(match_id, mercado)

    if consultar:
        resultado = api_client.get_predictions(match_id, market=mercado)
        if resultado and "predictions" in resultado:
            # Normalizar formato de la consulta al mismo shape que la generación
            resultado["predictions"] = [
                {**p, "label": f"Más de {p['line']} {MERCADOS[mercado].lower()}"}
                for p in resultado["predictions"]
            ]

    if resultado and "predictions" in resultado and resultado["predictions"]:
        st.divider()

        confianza = resultado.get("confidence_level", "low")
        muestra = resultado.get("sample_size", "?")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nivel de confianza", f"{CONFIANZA_COLOR.get(confianza, '⚪')} {CONFIANZA_TEXTO.get(confianza, confianza)}")
        with col2:
            st.metric("Tamaño de muestra", muestra)
        with col3:
            st.metric("Modelo", resultado.get("model_version", "—"))

        if confianza == "low":
            st.warning(
                "⚠️ Confianza baja: la muestra histórica disponible para uno o ambos equipos "
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
            with st.expander("Ver contexto del partido (forma, H2H, árbitro, motivación)"):
                st.json(resultado["context"])