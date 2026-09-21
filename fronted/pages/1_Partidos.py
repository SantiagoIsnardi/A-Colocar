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

_sync_info = api_client.get_last_sync()
if _sync_info and _sync_info.get("sofascore"):
    from datetime import datetime, timezone

    _last = datetime.fromisoformat(_sync_info["sofascore"])
    _delta = datetime.now(timezone.utc) - _last
    _horas = _delta.total_seconds() / 3600

    if _horas < 1:
        _texto = f"hace {int(_delta.total_seconds() / 60)} min"
    elif _horas < 48:
        _texto = f"hace {int(_horas)} hs"
    else:
        _texto = f"hace {int(_horas / 24)} días"

    _alerta = _horas > 30  # más de ~30hs sin sync es señal de que algo falló
    if _alerta:
        st.warning(f"⚠️ Sofascore no sincroniza hace {_texto} — puede que el status/resultado de hoy no esté al día.")
    else:
        st.caption(f"Datos de Sofascore actualizados {_texto}")

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
                "Hora": p["match_time_arg"],
                "Estado": p["status"],
            }
            for p in partidos
        ]
        st.dataframe(tabla, use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay partidos cargados para el {fecha.isoformat()}.")

st.divider()
st.markdown("### Buscar un partido puntual")
st.caption("Si no aparece en la tabla de arriba (fecha futura o pasada), buscalo por nombre de equipo.")

nombre = st.text_input("Nombre del equipo", placeholder="Ej: River, Barcelona, Boca...")

if nombre and len(nombre) >= 2:
    resultado_busqueda = api_client.search_teams(nombre)
    equipos = resultado_busqueda.get("teams", []) if resultado_busqueda else []

    if not equipos:
        st.info(f"No se encontró ningún equipo que coincida con \"{nombre}\".")
    else:
        opciones = {f"{e['name']} ({e['country'] or '—'})": e["id"] for e in equipos}
        seleccion = st.selectbox("Equipo encontrado", options=list(opciones.keys()))
        equipo_id = opciones[seleccion]

        col_a, col_b = st.columns(2)
        with col_a:
            filtro_status = st.selectbox(
                "Filtrar por",
                options=[None, "scheduled", "finished"],
                format_func=lambda x: {"None": "Todos", "scheduled": "Próximos", "finished": "Jugados"}.get(str(x), x),
            )
        with col_b:
            st.write("")  # espaciador visual

        partidos_equipo = api_client.get_matches_by_team(equipo_id, status=filtro_status)

        if partidos_equipo and partidos_equipo.get("matches"):
            tabla_equipo = [
                {
                    "ID": p["id"],
                    "Local": p["home_team"],
                    "Visitante": p["away_team"],
                    "Liga": p["league"],
                    "Fecha": p["match_date"][:10],
                    "Estado": p["status"],
                }
                for p in partidos_equipo["matches"]
            ]
            st.dataframe(tabla_equipo, use_container_width=True, hide_index=True)
        else:
            st.info("Ese equipo no tiene partidos cargados con ese filtro.")