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

STATUS_BADGES = {
    "SCHEDULED": "Próximo",
    "NS": "Próximo",
    "FINISHED": "Finalizado",
    "FT": "Finalizado",
    "IN_PLAY": "🔴 En Vivo",
}

_sync_info = api_client.get_last_sync()
if _sync_info:
    _last_official = _sync_info.get("football_data") or _sync_info.get("api_football") or _sync_info.get("sofascore")
    if _last_official:
        from datetime import datetime, timezone

        _last = datetime.fromisoformat(_last_official)
        _delta = datetime.now(timezone.utc) - _last
        _horas = _delta.total_seconds() / 3600

        if _horas < 1:
            _texto = f"hace {int(_delta.total_seconds() / 60)} min"
        elif _horas < 48:
            _texto = f"hace {int(_horas)} hs"
        else:
            _texto = f"hace {int(_horas / 24)} días"

        _alerta = _horas > 30
        if _alerta:
            st.warning(f"El fixture no se sincroniza hace {_texto} — puede que los partidos/resultados no estén al día.")
        else:
            st.caption(f"Sincronización de datos actualizada {_texto}")

fecha = st.date_input("Fecha", value=date.today())

resultado = api_client.get_matches_by_date(fecha.isoformat())

if resultado:
    partidos = resultado.get("matches", [])
    if partidos:
        st.caption(f"{resultado['count']} partido(s) el {resultado['date']}")

        # Selector de partido rápido para ir directamente a Predicciones o Value Bets
        opciones_partidos = {
            f"[{p['id']}] {p['match_time_arg']} hs | {p['home_team']} vs {p['away_team']} ({p['league']}) - {STATUS_BADGES.get(p['status'], p['status'])}": p["id"]
            for p in partidos
        }

        col_sel, col_btn1, col_btn2 = st.columns([3, 1, 1])
        with col_sel:
            partido_sel = st.selectbox("Seleccionar partido para analizar", options=list(opciones_partidos.keys()), label_visibility="collapsed")
        with col_btn1:
            if st.button("Ver Predicciones", use_container_width=True):
                st.session_state["selected_match_id"] = opciones_partidos[partido_sel]
                st.switch_page("pages/2_Predicciones.py")
        with col_btn2:
            if st.button("Ver Value Bets", use_container_width=True):
                st.session_state["selected_match_id"] = opciones_partidos[partido_sel]
                st.switch_page("pages/3_Apuestas_de_Valor.py")

        tabla = [
            {
                "ID": p["id"],
                "Hora": p["match_time_arg"],
                "Local": p["home_team"],
                "Resultado / Vs": f"{p.get('home_score', '-')} - {p.get('away_score', '-')}" if p["status"] in ["FINISHED", "FT"] else "vs",
                "Visitante": p["away_team"],
                "Liga": p["league"],
                "Estado": STATUS_BADGES.get(p["status"], p["status"]),
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
            opciones_partidos_equipo = {
                f"[{p['id']}] {p['match_date'][:10]} | {p['home_team']} vs {p['away_team']} ({p['league']}) - {STATUS_BADGES.get(p['status'], p['status'])}": p["id"]
                for p in partidos_equipo["matches"]
            }

            col_sel_eq, col_btn1_eq, col_btn2_eq = st.columns([3, 1, 1])
            with col_sel_eq:
                partido_sel_eq = st.selectbox("Seleccionar partido del equipo", options=list(opciones_partidos_equipo.keys()), key="sel_eq_match", label_visibility="collapsed")
            with col_btn1_eq:
                if st.button("Ver Predicciones", key="btn_pred_eq", use_container_width=True):
                    st.session_state["selected_match_id"] = opciones_partidos_equipo[partido_sel_eq]
                    st.switch_page("pages/2_Predicciones.py")
            with col_btn2_eq:
                if st.button("Ver Value Bets", key="btn_vb_eq", use_container_width=True):
                    st.session_state["selected_match_id"] = opciones_partidos_equipo[partido_sel_eq]
                    st.switch_page("pages/3_Apuestas_de_Valor.py")

            tabla_equipo = [
                {
                    "ID": p["id"],
                    "Fecha": p["match_date"][:10],
                    "Local": p["home_team"],
                    "Resultado / Vs": f"{p.get('home_score', '-')} - {p.get('away_score', '-')}" if p["status"] in ["FINISHED", "FT"] else "vs",
                    "Visitante": p["away_team"],
                    "Liga": p["league"],
                    "Estado": STATUS_BADGES.get(p["status"], p["status"]),
                }
                for p in partidos_equipo["matches"]
            ]
            st.dataframe(tabla_equipo, use_container_width=True, hide_index=True)
        else:
            st.info("Ese equipo no tiene partidos cargados con ese filtro.")