"""
Página de Partidos: muestra los partidos del día por defecto, con opción
de cambiar de fecha o buscar un partido puntual por su match_id (por si
no aparece en el listado, ya sea futuro o pasado).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from components import api_client
from components.theme import inject_background
from components.display import render_result

st.set_page_config(page_title="Partidos", layout="wide")
inject_background()

st.title("Partidos")

fecha = st.date_input("Fecha", value=date.today())

resultado = api_client.get_matches_by_date(fecha.isoformat())

if resultado:
    partidos = resultado.get("matches", [])
    if partidos:
        st.caption(f"{resultado['count']} partido(s) el {resultado['date']}")
        tabla = [
            {
                "ID": p["id"],
                "Local": p["home_team"],
                "Visitante": p["away_team"],
                "Liga": p["league"],
                "Hora": p["match_date"][11:16],
                "Estado": p["status"],
            }
            for p in partidos
        ]
        st.dataframe(tabla, use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay partidos cargados para el {fecha.isoformat()}.")

st.divider()
st.markdown("### Buscar un partido puntual")
st.caption("Si no aparece en la tabla de arriba (fecha futura o pasada distinta), buscalo acá por su ID.")

match_id = st.number_input("Match ID", min_value=1, step=1, value=None)

if match_id:
    partido = api_client.get_match(int(match_id))
    if partido:
        render_result(partido, title=f"Partido #{match_id}")