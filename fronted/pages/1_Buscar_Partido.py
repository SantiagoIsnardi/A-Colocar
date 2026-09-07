"""
Página de búsqueda: permite encontrar el match_id de un partido a partir
del nombre de un equipo, consultando directamente la base vía backend.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from components import api_client

st.set_page_config(page_title="Buscar Partido", page_icon="🔍", layout="wide")
st.title("🔍 Buscar Partido")

st.info(
    "Esta versión inicial requiere que conozcas el `match_id` directamente "
    "(consultalo en tu base de datos). La búsqueda por nombre de equipo se "
    "agrega en una iteración posterior."
)

match_id = st.number_input("Match ID", min_value=1, step=1, value=None)

if match_id:
    st.divider()
    st.subheader(f"Partido #{match_id}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Predicciones de goles")
        if st.button("Consultar predicciones existentes", key="get_pred"):
            result = api_client.get_predictions(match_id, market="goals")
            if result:
                st.json(result)

        if st.button("Generar nueva predicción", key="gen_pred"):
            with st.spinner("Calculando..."):
                result = api_client.generate_goal_predictions(match_id)
            if result:
                st.json(result)

    with col2:
        st.markdown("### Cuotas de mercado")
        if st.button("Consultar cuotas", key="get_odds"):
            result = api_client.get_match_odds(match_id, market="goals")
            if result:
                st.json(result)
                