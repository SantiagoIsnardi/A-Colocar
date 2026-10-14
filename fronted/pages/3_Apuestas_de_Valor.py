"""
Página de Value Bets: muestra las apuestas de valor detectadas para un
partido específico, o el ranking general de las mejores oportunidades
en toda la base de datos.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
from components import api_client

st.set_page_config(page_title="Value Bets", layout="wide")
st.title("Apuestas de Valor")

MERCADOS_LABEL = {
    "goals": "Goles",
    "corners": "Corners",
    "yellow_cards": "Tarjetas Amarillas",
    "fouls": "Faltas",
    "shots": "Tiros",
}

tab1, tab2 = st.tabs(["Por partido", "Ranking general"])

with tab1:
    st.subheader("Value bets de un partido específico")
    default_match_id = st.session_state.get("selected_match_id", None)
    match_id = st.number_input("Match ID", min_value=1, step=1, value=default_match_id, key="vb_match_id")

    if match_id:
        result = api_client.get_value_bets(match_id)

        if result and result.get("value_bets"):
            df = pd.DataFrame(result["value_bets"])
            df = df.rename(columns={
                "market": "Mercado",
                "line": "Línea",
                "side": "Lado",
                "edge_percentage": "Edge (%)",
                "expected_value": "Valor Esperado",
                "kelly_stake_pct": "Stake Kelly (%)",
                "price": "Cuota",
                "status": "Estado",
            })
            if "Stake Kelly (%)" in df.columns:
                df["Stake Kelly (%)"] = (df["Stake Kelly (%)"] * 100).round(2)

            columnas = [c for c in ["Mercado", "Línea", "Lado", "Cuota", "Edge (%)", "Valor Esperado", "Stake Kelly (%)", "Estado"] if c in df.columns]
            st.dataframe(
                df[columnas],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "El 'Stake Kelly' es una sugerencia matemática, no una recomendación de inversión. "
                "Edges muy altos (>15%) suelen indicar cuotas de referencia poco realistas."
            )
        elif result:
            st.info("No se encontraron apuestas de valor para este partido.")

with tab2:
    st.subheader("Mejores oportunidades detectadas")
    market_filter = st.selectbox(
        "Filtrar por mercado",
        options=[None, "goals", "corners", "yellow_cards", "fouls", "shots"],
        format_func=lambda x: "Todos" if x is None else MERCADOS_LABEL.get(x, x),
    )

    if st.button("Consultar ranking", use_container_width=True):
        result = api_client.get_rankings(market=market_filter)
        if result and "markets" in result:
            markets_data = result["markets"]
            hay_datos = False

            for mkt, bets in markets_data.items():
                if not bets:
                    continue
                hay_datos = True

                st.subheader(MERCADOS_LABEL.get(mkt, mkt.capitalize()))
                df_ranking = pd.DataFrame(bets)

                columnas_disponibles = [c for c in [
                    "match_id", "line", "side", "price", "edge_percentage",
                    "expected_value", "kelly_stake_pct"
                ] if c in df_ranking.columns]

                df_mostrar = df_ranking[columnas_disponibles].rename(columns={
                    "match_id": "Partido ID",
                    "line": "Línea",
                    "side": "Lado",
                    "price": "Cuota",
                    "edge_percentage": "Edge (%)",
                    "expected_value": "Valor Esperado",
                    "kelly_stake_pct": "Stake Kelly",
                })

                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                st.divider()

            if not hay_datos:
                st.info("No hay value bets registradas todavía.")
        elif result is not None:
            st.warning("El servidor respondió pero no se encontraron oportunidades.")