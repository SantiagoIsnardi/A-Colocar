"""
Componente reutilizable: selector de partido por nombre de equipo.

El flujo para el usuario es:
  1. Escribe el nombre de un equipo (búsqueda insensible a mayúsculas y acentos).
  2. Elige el equipo del dropdown.
  3. Elige el partido de ese equipo del dropdown, priorizando:
     - Partidos de HOY en primer lugar
     - Partidos FUTUROS (ordenados del más cercano en adelante)
     - Partidos PASADOS (ordenados del más reciente hacia atrás)
  4. Devuelve el match_id seleccionado.

Si hay un `selected_match_id` en session_state (venimos de la página Partidos),
muestra el enfrentamiento preseleccionado sin pedir búsqueda manual.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from components import api_client

ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

STATUS_LABEL = {
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


def _parse_match_datetime(raw_date: str | None) -> datetime:
    """Parsea una fecha ISO y la convierte a zona horaria de Argentina."""
    if not raw_date:
        return datetime.now(ARG_TZ)
    try:
        dt = datetime.fromisoformat(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ARG_TZ)
    except Exception:
        return datetime.now(ARG_TZ)


def _format_match_option(p: dict, today_arg) -> str:
    """Texto legible y sin símbolos para un partido en el selectbox."""
    dt_arg = _parse_match_datetime(p.get("match_date") or p.get("match_date_utc"))
    m_date = dt_arg.date()

    home = p.get("home_team", "?")
    away = p.get("away_team", "?")
    league = p.get("league", "")
    raw_status = p.get("status", "")

    # Determinar estado semántico según fecha y status de BD
    if m_date == today_arg:
        if raw_status in ("live", "IN_PLAY"):
            estado = "En Vivo"
        elif raw_status in ("finished", "FINISHED", "FT"):
            estado = "Finalizado"
        else:
            estado = "Próximo"
        return f"HOY {dt_arg.strftime('%H:%M')} hs | {home} vs {away} ({league}) — {estado}"

    elif m_date > today_arg:
        estado = "Próximo"
        return f"{dt_arg.strftime('%d/%m %H:%M')} hs | {home} vs {away} ({league}) — {estado}"

    else:
        # Si la fecha ya pasó, jamás mostrar "Próximo" aunque la BD no se haya actualizado
        estado = "Finalizado" if raw_status in ("finished", "FINISHED", "FT", "scheduled", "SCHEDULED", "TIMED", "NS") else STATUS_LABEL.get(raw_status, "Finalizado")
        return f"{dt_arg.strftime('%d/%m %H:%M')} hs | {home} vs {away} ({league}) — {estado}"


def match_selector(key_prefix: str = "ms") -> int | None:
    """
    Widget de búsqueda de partido por nombre de equipo.

    Args:
        key_prefix: prefijo para las keys de session_state y widgets de Streamlit.

    Returns:
        match_id (int) si se seleccionó un partido, o None si no.
    """
    preselected_id = st.session_state.get("selected_match_id")

    # ── Caso: venimos de Partidos con un match_id ya elegido ──────────────────
    if preselected_id:
        match_info = api_client.get_match(preselected_id)
        if match_info:
            home = match_info.get("home_team") or f"Equipo #{match_info.get('home_team_id')}"
            away = match_info.get("away_team") or f"Equipo #{match_info.get('away_team_id')}"
            league = match_info.get("league", "")
            raw_date = match_info.get("match_date", "")
            date_str = ""
            if raw_date:
                dt_arg = _parse_match_datetime(raw_date)
                date_str = dt_arg.strftime("%d/%m/%Y %H:%M hs")

            st.info(
                f"Partido preseleccionado: **{home} vs {away}** · {league} · {date_str}"
            )
            col_keep, col_change = st.columns([3, 1])
            with col_keep:
                st.caption("Podés cambiar el partido buscando otro equipo abajo.")
            with col_change:
                if st.button("Cambiar partido", key=f"{key_prefix}_clear", use_container_width=True):
                    del st.session_state["selected_match_id"]
                    st.rerun()
            return preselected_id

    # ── Búsqueda por nombre de equipo ─────────────────────────────────────────
    st.markdown("##### Buscar partido por equipo")

    query = st.text_input(
        "Nombre del equipo",
        placeholder="Ej: River, Boca, Velez, Bayern...",
        key=f"{key_prefix}_query",
    )

    if not query or len(query.strip()) < 2:
        st.caption("Escribí al menos 2 letras para buscar un equipo.")
        return None

    # Búsqueda de equipos insensible a acentos
    equipos_result = api_client.search_teams(query.strip(), limit=15)
    equipos = equipos_result.get("teams", []) if equipos_result else []

    if not equipos:
        st.warning(f"No se encontró ningún equipo que coincida con \"{query}\".")
        return None

    # Deduplicar equipos por nombre para no mostrar opciones duplicadas en el dropdown
    opciones_equipos: dict[str, int] = {}
    for e in equipos:
        label = f"{e['name']} ({e.get('country') or '—'})"
        if label not in opciones_equipos:
            opciones_equipos[label] = e["id"]

    equipo_label = st.selectbox(
        "Equipo encontrado",
        options=list(opciones_equipos.keys()),
        key=f"{key_prefix}_team",
        label_visibility="collapsed",
    )
    equipo_id = opciones_equipos[equipo_label]

    # Traer todos los partidos del equipo (el backend ya unifica IDs equivalentes)
    partidos_result = api_client.get_matches_by_team(equipo_id, limit=30)
    lista_partidos: list[dict] = partidos_result.get("matches", []) if partidos_result else []

    if not lista_partidos:
        equipo_puro = equipo_label.split("(")[0].strip()
        st.info(f"No se encontraron partidos registrados para {equipo_puro}.")
        return None

    today_arg = datetime.now(ARG_TZ).date()

    # Clasificar en tres grupos:
    # 1. HOY: partidos cuya fecha en Argentina es hoy
    # 2. FUTUROS: partidos posteriores a hoy (más cercanos primero)
    # 3. PASADOS: partidos anteriores a hoy (más recientes primero)
    partidos_hoy: list[dict] = []
    partidos_futuros: list[dict] = []
    partidos_pasados: list[dict] = []

    for p in lista_partidos:
        dt = _parse_match_datetime(p.get("match_date") or p.get("match_date_utc"))
        p["_dt_arg"] = dt
        m_date = dt.date()
        if m_date == today_arg:
            partidos_hoy.append(p)
        elif m_date > today_arg:
            partidos_futuros.append(p)
        else:
            partidos_pasados.append(p)

    # Ordenar cada grupo
    partidos_hoy = sorted(partidos_hoy, key=lambda p: p["_dt_arg"])
    partidos_futuros = sorted(partidos_futuros, key=lambda p: p["_dt_arg"])
    partidos_pasados = sorted(partidos_pasados, key=lambda p: p["_dt_arg"], reverse=True)

    lista_ordenada = partidos_hoy + partidos_futuros + partidos_pasados

    opciones_partidos = {
        _format_match_option(p, today_arg): p["id"]
        for p in lista_ordenada
    }

    partido_label = st.selectbox(
        "Seleccionar partido",
        options=list(opciones_partidos.keys()),
        key=f"{key_prefix}_match",
        label_visibility="collapsed",
    )
    match_id = opciones_partidos[partido_label]

    st.session_state["selected_match_id"] = match_id
    return match_id
