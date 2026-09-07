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

st.set_page_config(page_title="Value Bets", page_icon="💰", layout="wide")
st.title("💰 Apuestas de Valor")

tab1, tab2 = st.tabs(["Por partido", "Ranking general"])

with tab1:
    st.subheader("Value bets de un partido específico")
    match_id = st.number_input("Match ID", min_value=1, step=1, value=None, key="vb_match_id")

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
            df["Stake Kelly (%)"] = (df["Stake Kelly (%)"] * 100).round(2)

            st.dataframe(
                df[["Mercado", "Línea", "Lado", "Cuota", "Edge (%)", "Valor Esperado", "Stake Kelly (%)", "Estado"]],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "⚠️ El 'Stake Kelly' es una sugerencia matemática, no una recomendación de inversión. "
                "Edges muy altos (>15%) suelen indicar cuotas de referencia poco realistas."
            )
        elif result:
            st.info("No se encontraron apuestas de valor para este partido.")

with tab2:
    st.subheader("Mejores oportunidades detectadas")
    market_filter = st.selectbox(
        "Filtrar por mercado",
        options=[None, "goals", "corners", "yellow_cards", "fouls", "shots"],
        format_func=lambda x: "Todos" if x is None else {
            "goals": "Goles", "corners": "Corners", "yellow_cards": "Amarillas",
            "fouls": "Faltas", "shots": "Tiros",
        }.get(x, x),
    )

    if st.button("Consultar ranking"):
        result = api_client.get_rankings(market=market_filter)
        if result:
            st.json(result)