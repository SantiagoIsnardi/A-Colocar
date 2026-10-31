"""
Página de Partidos: muestra los partidos del día por defecto, con opción
de cambiar de fecha o buscar un partido puntual por su equipo (por si
no aparece en el listado, ya sea futuro o pasado).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from components import api_client
from components.theme import inject_background

ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

st.set_page_config(page_title="Partidos", layout="wide")
inject_background()

st.title("Partidos")

STATUS_BADGES = {
    "SCHEDULED": "Próximo",
    "scheduled": "Próximo",
    "TIMED": "Próximo",
    "NS": "Próximo",
    "FINISHED": "Finalizado",
    "finished": "Finalizado",
    "FT": "Finalizado",
    "IN_PLAY": "En Vivo",
    "live": "En Vivo",
}

_sync_info = api_client.get_last_sync()
if _sync_info:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        _fd_last = _sync_info.get("football_data")
        if _fd_last:
            _delta = datetime.now(timezone.utc) - datetime.fromisoformat(_fd_last)
            _hs = int(_delta.total_seconds() / 3600)
            _txt = f"{int(_delta.total_seconds() / 60)} min" if _hs < 1 else f"{_hs} hs"
            st.caption(f"**Ligas Europeas:** sincronizado hace {_txt}")
        else:
            st.caption("**Ligas Europeas:** sin datos")
    with col_s2:
        _sofa_last = _sync_info.get("sofascore") or _sync_info.get("api_football")
        if _sofa_last:
            _delta = datetime.now(timezone.utc) - datetime.fromisoformat(_sofa_last)
            _dias = int(_delta.total_seconds() / 86400)
            if _dias > 1:
                st.caption(f"**Sudamérica (Sofascore/API):** última ingesta hace {_dias} días (requiere scraper local)")
            else:
                _hs = int(_delta.total_seconds() / 3600)
                st.caption(f"**Sudamérica (Sofascore/API):** hace {_hs} hs")
        else:
            st.caption("**Sudamérica (Sofascore/API):** sin datos")

# Usar horario de Argentina para que en Streamlit Cloud (UTC) no se adelante el día a las 21:00 ART
fecha = st.date_input("Fecha", value=datetime.now(ARG_TZ).date())

resultado = api_client.get_matches_by_date(fecha.isoformat())

if resultado:
    partidos = resultado.get("matches", [])
    if partidos:
        st.caption(f"{resultado['count']} partido(s) el {resultado['date']}")

        # Selector de partido rápido para ir directamente a Predicciones o Value Bets
        opciones_partidos = {
            f"{p['match_time_arg']} hs | {p['home_team']} vs {p['away_team']} ({p['league']}) — {STATUS_BADGES.get(p['status'], p['status'])}": p["id"]
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
                "Resultado / Vs": f"{p.get('home_score', '-')} - {p.get('away_score', '-')}" if p["status"] in ["FINISHED", "finished", "FT"] else "vs",
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

nombre = st.text_input("Nombre del equipo", placeholder="Ej: River, Boca, Velez, Bayern...")

if nombre and len(nombre) >= 2:
    resultado_busqueda = api_client.search_teams(nombre)
    equipos = resultado_busqueda.get("teams", []) if resultado_busqueda else []

    if not equipos:
        st.info(f"No se encontró ningún equipo que coincida con \"{nombre}\".")
    else:
        # Deduplicar por nombre
        opciones: dict[str, int] = {}
        for e in equipos:
            lbl = f"{e['name']} ({e.get('country') or '—'})"
            if lbl not in opciones:
                opciones[lbl] = e["id"]

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

        partidos_equipo = api_client.get_matches_by_team(equipo_id, status=filtro_status, limit=30)
        raw_matches = partidos_equipo.get("matches", []) if partidos_equipo else []

        if raw_matches:
            today_arg = datetime.now(ARG_TZ).date()

            # Clasificar y ordenar: HOY primero, Futuros, Pasados
            partidos_hoy = []
            partidos_futuros = []
            partidos_pasados = []

            for p in raw_matches:
                raw_d = p.get("match_date") or p.get("match_date_utc", "")
                try:
                    dt = datetime.fromisoformat(raw_d)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    dt_arg = dt.astimezone(ARG_TZ)
                except Exception:
                    dt_arg = datetime.now(ARG_TZ)

                p["_dt_arg"] = dt_arg
                m_date = dt_arg.date()

                if m_date == today_arg:
                    partidos_hoy.append(p)
                elif m_date > today_arg:
                    partidos_futuros.append(p)
                else:
                    partidos_pasados.append(p)

            # Orden: hoy por hora asc, futuros por fecha asc, pasados por fecha desc
            partidos_hoy = sorted(partidos_hoy, key=lambda p: p["_dt_arg"])
            partidos_futuros = sorted(partidos_futuros, key=lambda p: p["_dt_arg"])
            partidos_pasados = sorted(partidos_pasados, key=lambda p: p["_dt_arg"], reverse=True)

            lista_ordenada = partidos_hoy + partidos_futuros + partidos_pasados

            def _fmt_match_label(p):
                dt_arg = p["_dt_arg"]
                m_date = dt_arg.date()
                raw_st = p.get("status", "")
                if m_date == today_arg:
                    st_txt = "En Vivo" if raw_st in ("live", "IN_PLAY") else ("Finalizado" if raw_st in ("finished", "FINISHED", "FT") else "Próximo")
                    return f"HOY {dt_arg.strftime('%H:%M')} hs | {p['home_team']} vs {p['away_team']} ({p['league']}) — {st_txt}"
                elif m_date > today_arg:
                    return f"{dt_arg.strftime('%d/%m %H:%M')} hs | {p['home_team']} vs {p['away_team']} ({p['league']}) — Próximo"
                else:
                    st_txt = "Finalizado" if raw_st in ("finished", "FINISHED", "FT", "scheduled", "SCHEDULED", "TIMED", "NS") else STATUS_BADGES.get(raw_st, "Finalizado")
                    return f"{dt_arg.strftime('%d/%m %H:%M')} hs | {p['home_team']} vs {p['away_team']} ({p['league']}) — {st_txt}"

            opciones_partidos_equipo = {
                _fmt_match_label(p): p["id"]
                for p in lista_ordenada
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
                    "Fecha": p["_dt_arg"].strftime("%d/%m/%Y %H:%M"),
                    "Local": p["home_team"],
                    "Resultado / Vs": f"{p.get('home_score', '-')} - {p.get('away_score', '-')}" if p["status"] in ["FINISHED", "finished", "FT"] else "vs",
                    "Visitante": p["away_team"],
                    "Liga": p["league"],
                    "Estado": "Finalizado" if p["_dt_arg"].date() < today_arg and p["status"] in ["scheduled", "SCHEDULED", "TIMED", "NS"] else STATUS_BADGES.get(p["status"], p["status"]),
                }
                for p in lista_ordenada
            ]
            st.dataframe(tabla_equipo, use_container_width=True, hide_index=True)
        else:
            st.info("Ese equipo no tiene partidos cargados con ese filtro.")
