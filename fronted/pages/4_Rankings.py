"""
Página de Rankings: muestra las mejores value bets detectadas en toda
la base de datos, ordenadas por edge, agrupadas por mercado.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
from components import api_client

st.set_page_config(page_title="Rankings", page_icon="🏆", layout="wide")
st.title("🏆 Rankings de Oportunidades")

MERCADOS_LABEL = {
    "goals": "Goles",
    "corners": "Corners",
    "yellow_cards": "Tarjetas Amarillas",
    "fouls": "Faltas",
    "shots": "Tiros",
}

limite = st.slider("Cantidad máxima por mercado", min_value=5, max_value=50, value=10)

if st.button("🔍 Consultar ranking", use_container_width=True):
    resultado = api_client.get_rankings(limit_per_market=limite)

    if resultado and "markets" in resultado:
        markets_data = resultado["markets"]
        hay_datos = False

        for mkt, bets in markets_data.items():
            if not bets:
                continue
            hay_datos = True

            st.subheader(MERCADOS_LABEL.get(mkt, mkt))
            df = pd.DataFrame(bets)

            columnas_disponibles = [c for c in [
                "match_id", "line", "side", "price", "edge_percentage",
                "expected_value", "kelly_stake_pct"
            ] if c in df.columns]

            df_mostrar = df[columnas_disponibles].rename(columns={
                "match_id": "Partido",
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
    elif resultado is not None:
        st.warning("El servidor respondió pero sin el formato esperado.")