"""
Componente reutilizable: selector de partido por nombre de equipo.

Uso:
    from components.match_selector import match_selector
    match_id = match_selector(key_prefix="pred")
    if match_id:
        # trabajar con match_id

El flujo para el usuario es:
  1. Escribe el nombre de un equipo (buscador fuzzy contra la API).
  2. Elige el equipo del dropdown.
  3. Elige el partido de ese equipo (próximos + recientes) del dropdown.
  4. Devuelve el match_id seleccionado.

Si hay un `selected_match_id` en session_state (venimos de la página Partidos),
lo usa como valor inicial y muestra el partido preseleccionado sin pedir búsqueda.
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
    "live": "🔴 En Vivo",
    "IN_PLAY": "🔴 En Vivo",
    "finished": "Finalizado",
    "FINISHED": "Finalizado",
    "FT": "Finalizado",
    "postponed": "Postergado",
    "cancelled": "Cancelado",
}


def _format_match_option(p: dict) -> str:
    """Texto legible para un partido en el selectbox."""
    date_str = ""
    raw_date = p.get("match_date") or p.get("match_date_utc", "")
    if raw_date:
        try:
            dt = datetime.fromisoformat(raw_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_arg = dt.astimezone(ARG_TZ)
            date_str = dt_arg.strftime("%d/%m %H:%M hs")
        except ValueError:
            date_str = raw_date[:10]

    home = p.get("home_team", "?")
    away = p.get("away_team", "?")
    league = p.get("league", "")
    status = STATUS_LABEL.get(p.get("status", ""), p.get("status", ""))

    return f"{date_str} | {home} vs {away} ({league}) — {status}"


def match_selector(key_prefix: str = "ms") -> int | None:
    """
    Widget de búsqueda de partido por nombre de equipo.

    Args:
        key_prefix: prefijo para las keys de session_state y widgets de Streamlit,
                    para evitar colisiones si se usa en más de una página.

    Returns:
        match_id (int) si se seleccionó un partido, o None si no.
    """
    preselected_id = st.session_state.get("selected_match_id")

    # ── Caso: venimos de Partidos con un match_id ya elegido ──────────────────
    if preselected_id:
        match_info = api_client.get_match(preselected_id)
        if match_info:
            home = match_info.get("home_team_id", "")
            away = match_info.get("away_team_id", "")
            league = match_info.get("league", "")
            raw_date = match_info.get("match_date", "")
            date_str = ""
            if raw_date:
                try:
                    dt = datetime.fromisoformat(raw_date)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    date_str = dt.astimezone(ARG_TZ).strftime("%d/%m/%Y %H:%M hs")
                except ValueError:
                    date_str = raw_date[:10]

            st.info(
                f"**Partido preseleccionado:** ID {preselected_id} · {league} · {date_str}",
                icon="⚽",
            )
            col_keep, col_change = st.columns([2, 1])
            with col_keep:
                st.caption("Podés cambiar el partido buscando un equipo abajo.")
            with col_change:
                if st.button("🔄 Cambiar partido", key=f"{key_prefix}_clear", use_container_width=True):
                    del st.session_state["selected_match_id"]
                    st.rerun()
            return preselected_id

    # ── Búsqueda por nombre de equipo ─────────────────────────────────────────
    st.markdown("##### Buscar partido por equipo")

    query = st.text_input(
        "Nombre del equipo",
        placeholder="Ej: River, Arsenal, Bayern...",
        key=f"{key_prefix}_query",
    )

    if not query or len(query.strip()) < 2:
        st.caption("Escribí al menos 2 letras para buscar un equipo.")
        return None

    # Búsqueda de equipos
    equipos_result = api_client.search_teams(query.strip(), limit=10)
    equipos = equipos_result.get("teams", []) if equipos_result else []

    if not equipos:
        st.warning(f"No se encontró ningún equipo que coincida con **\"{query}\"**.")
        return None

    # Selector de equipo
    opciones_equipos = {
        f"{e['name']} ({e.get('country') or '—'})": e["id"]
        for e in equipos
    }
    equipo_label = st.selectbox(
        "Equipo encontrado",
        options=list(opciones_equipos.keys()),
        key=f"{key_prefix}_team",
        label_visibility="collapsed",
    )
    equipo_id = opciones_equipos[equipo_label]

    # Traer partidos de ese equipo (próximos primero, luego recientes)
    proximos = api_client.get_matches_by_team(equipo_id, status="scheduled", limit=10)
    recientes = api_client.get_matches_by_team(equipo_id, status="finished", limit=5)

    lista_partidos: list[dict] = []
    if proximos:
        lista_partidos += proximos.get("matches", [])
    if recientes:
        lista_partidos += recientes.get("matches", [])

    if not lista_partidos:
        st.info(f"No se encontraron partidos para **{equipo_label.split('(')[0].strip()}** con ese filtro.")
        return None

    # Deduplicar por id (puede venir de ambas listas)
    seen_ids: set = set()
    lista_dedup: list[dict] = []
    for p in lista_partidos:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            lista_dedup.append(p)

    # Ordenar: primero próximos (por fecha asc), luego finalizados (desc)
    proximos_ord = sorted(
        [p for p in lista_dedup if p.get("status") not in ("finished", "FINISHED", "FT")],
        key=lambda p: p.get("match_date", ""),
    )
    finalizados_ord = sorted(
        [p for p in lista_dedup if p.get("status") in ("finished", "FINISHED", "FT")],
        key=lambda p: p.get("match_date", ""),
        reverse=True,
    )
    lista_final = proximos_ord + finalizados_ord

    opciones_partidos = {
        _format_match_option(p): p["id"]
        for p in lista_final
    }

    partido_label = st.selectbox(
        "Seleccionar partido",
        options=list(opciones_partidos.keys()),
        key=f"{key_prefix}_match",
        label_visibility="collapsed",
    )
    match_id = opciones_partidos[partido_label]

    # Guardar en session_state para que otros widgets lo detecten
    st.session_state["selected_match_id"] = match_id
    return match_id
