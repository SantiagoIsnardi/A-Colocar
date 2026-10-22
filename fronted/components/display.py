"""
Renderizado genérico de resultados del backend (dicts anidados) como
tarjetas y métricas, en vez de volcar el JSON crudo con st.json(),
junto con componentes especializados como render_match_context.
"""

import streamlit as st

# Campos técnicos que no le sirven al usuario final, se ocultan siempre.
_HIDDEN_KEYS = {"model_version", "computed_at"}

# Traducciones. Si un campo no está acá, se muestra igual (capitalizado),
# pero conviene ir completando esta lista a medida que aparezcan nuevos.
_LABELS = {
    "probability_over": "Probabilidad",
    "percentage": "Porcentaje",
    "confidence_level": "Confianza",
    "sample_size": "Muestra evaluada",
    "line": "Línea",
    "lambda_home": "λ local",
    "lambda_away": "λ visitante",
    "home_attack_multiplier": "Mult. ataque local",
    "away_attack_multiplier": "Mult. ataque visitante",
    "match_id": "Partido",
    "market": "Mercado",

    # Forma
    "form_score": "Forma",
    "avg_points_per_match": "Puntos prom./partido",
    "sufficient": "Muestra suficiente",

    # Head to head
    "home_wins": "Victorias local",
    "draws": "Empates",
    "away_wins": "Victorias visitante",
    "home_win_rate": "% victorias local",
    "avg_home_goals": "Goles prom. local",
    "avg_away_goals": "Goles prom. visitante",

    # Motivación
    "trend_score": "Tendencia",
    "recent_avg_points": "Puntos prom. (reciente)",
    "older_avg_points": "Puntos prom. (anterior)",

    # Árbitro
    "available": "Datos disponibles",
    "referee_name": "Árbitro",
    "avg_yellow_cards_per_match": "Amarillas prom./partido",
    "avg_red_cards_per_match": "Rojas prom./partido",
    "avg_fouls_per_match": "Faltas prom./partido",

    # Contexto general
    "home_form": "Forma local",
    "away_form": "Forma visitante",
    "head_to_head": "Historial entre ambos",
    "referee_profile": "Perfil del árbitro",
    "home_motivation": "Motivación local",
    "away_motivation": "Motivación visitante",

    # Calibración / Rendimiento
    "avg_brier_score": "Precisión del modelo (Brier)",
    "accuracy_simple": "Aciertos",
    "avg_clv_percentage": "Valor vs. cierre de mercado (CLV)",
    "clv_sample_size": "Casos con CLV calculado",
    "model_version_filter": "Versión del modelo",
}

# Campos de texto libre (pueden ser largos): se muestran aparte, nunca
# como métrica, para que no se corten.
_TEXT_KEYS = {"reason", "note"}

# Umbral: strings más largos que esto tampoco van a métrica, por las dudas
# aparezca un texto largo en un campo que no anticipamos.
_MAX_METRIC_TEXT = 18


def _label(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " ").capitalize())


_PERCENT_KEYS = {"accuracy_simple", "avg_clv_percentage"}


def _fmt(value, key: str = "") -> str:
    if isinstance(value, float):
        if key in _PERCENT_KEYS:
            return f"{value * 100:.1f}%"
        return f"{value:.3f}" if abs(value) < 10 else f"{value:.1f}"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def render_result(data: dict, title: str | None = None) -> None:
    """
    Muestra un dict del backend como tarjetas de métricas + secciones
    expandibles para sub-dicts y tablas para listas de dicts.
    """
    if title:
        st.subheader(title)

    data = {k: v for k, v in data.items() if k not in _HIDDEN_KEYS}

    texts = {
        k: v for k, v in data.items()
        if isinstance(v, str) and (k in _TEXT_KEYS or len(v) > _MAX_METRIC_TEXT)
    }
    scalars = {
        k: v for k, v in data.items()
        if isinstance(v, (int, float, bool)) or (isinstance(v, str) and k not in texts)
    }
    nested_dicts = {k: v for k, v in data.items() if isinstance(v, dict)}
    lists_of_dicts = {
        k: v for k, v in data.items()
        if isinstance(v, list) and v and all(isinstance(item, dict) for item in v)
    }

    if scalars:
        cols = st.columns(min(len(scalars), 4))
        for i, (key, value) in enumerate(scalars.items()):
            with cols[i % len(cols)]:
                st.metric(_label(key), _fmt(value, key))

    for key, value in texts.items():
        st.caption(f"**{_label(key)}:** {value}")

    for key, items in lists_of_dicts.items():
        cleaned = [{k: v for k, v in item.items() if k not in _HIDDEN_KEYS} for item in items]
        st.markdown(f"**{_label(key)}**")
        st.dataframe(cleaned, use_container_width=True, hide_index=True)

    for key, sub in nested_dicts.items():
        with st.expander(_label(key)):
            render_result(sub)


def _format_attack_multiplier(mult: float) -> tuple[str, str]:
    diff_pct = (mult - 1.0) * 100
    sign = "+" if diff_pct > 0 else ""
    diff_str = f"{sign}{diff_pct:.1f}% vs promedio liga"

    if mult >= 1.15:
        category = "Ataque Potente"
    elif mult > 1.02:
        category = "Superior al promedio"
    elif mult >= 0.98:
        category = "Promedio de la liga"
    elif mult >= 0.85:
        category = "Levemente inferior al promedio"
    else:
        category = "Ataque Reducido"

    label = f"{category} ({mult:.2f}x)"
    return label, diff_str


def _format_form_score(score: float) -> tuple[str, int]:
    pct = max(0, min(100, int(round(score * 100))))
    if pct >= 65:
        label = f"Alta ({pct}%)"
    elif pct >= 40:
        label = f"Media ({pct}%)"
    else:
        label = f"Baja ({pct}%)"
    return label, pct


def _format_trend_score(score: float) -> str:
    if score >= 0.55:
        return "📈 En alza (Mejorando racha)"
    elif score <= 0.45:
        return "📉 En declive (Bajo rendimiento reciente)"
    return "➡️ Rendimiento estable"


def render_match_context(context: dict) -> None:
    """
    Renderiza de forma intuitiva, visual y sin jerga técnica el contexto
    del partido (poder ofensivo, forma reciente, tendencia, H2H y árbitro).
    """
    if not context:
        st.info("Sin datos de contexto disponibles para este partido.")
        return

    # 1. Multiplicadores de ataque
    home_mult = context.get("home_attack_multiplier", 1.0)
    away_mult = context.get("away_attack_multiplier", 1.0)

    home_label, home_diff = _format_attack_multiplier(home_mult)
    away_label, away_diff = _format_attack_multiplier(away_mult)

    st.markdown("##### ⚡ Multiplicador de Ataque (Poder Ofensivo)")
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.metric(
            label="Ataque Local",
            value=home_label,
            delta=home_diff,
            help="Indica el poder de gol del equipo local comparado con el promedio del torneo (1.00x = promedio)."
        )
    with c_m2:
        st.metric(
            label="Ataque Visitante",
            value=away_label,
            delta=away_diff,
            help="Indica el poder de gol del equipo visitante comparado con el promedio del torneo (1.00x = promedio)."
        )

    st.divider()

    # 2. Forma y Motivación
    st.markdown("#### Estado de Forma y Tendencia")
    c_f1, c_f2 = st.columns(2)

    home_form = context.get("home_form") or {}
    home_mot = context.get("home_motivation") or {}

    with c_f1:
        st.markdown("**Local**")
        h_score = home_form.get("form_score", 0.5)
        h_lbl, h_pct = _format_form_score(h_score)
        h_pts = home_form.get("avg_points_per_match", 0.0)
        h_sample = home_form.get("sample_size", 0)
        h_suff = home_form.get("sufficient", False)

        st.metric(
            label="Forma Reciente",
            value=h_lbl,
            delta=f"{h_pts:.1f} pts / partido",
            help="Rendimiento del equipo en sus últimos partidos ponderados por antigüedad (0% = racha negativa, 100% = racha perfecta)."
        )
        st.progress(h_pct / 100.0)

        # Motivación / Tendencia
        h_trend = home_mot.get("trend_score", 0.5)
        st.markdown(
            f"**Tendencia:** {_format_trend_score(h_trend)}",
            help="Compara el rendimiento de los partidos más recientes contra los anteriores para detectar si el equipo viene en alza o en baja."
        )
        if "recent_avg_points" in home_mot and "older_avg_points" in home_mot:
            st.caption(f"Últimos juegos: {home_mot['recent_avg_points']:.1f} pts vs Previos: {home_mot['older_avg_points']:.1f} pts")

        # Indicador de confianza amigable
        if h_suff:
            st.markdown(f"🟢 **Confianza Alta** `(Basado en {h_sample} partidos)`")
        else:
            st.markdown(f"🟡 **Confianza Limitada** `(Solo {h_sample} partido{'s' if h_sample != 1 else ''} evaluado{'s' if h_sample != 1 else ''})`")

    away_form = context.get("away_form") or {}
    away_mot = context.get("away_motivation") or {}

    with c_f2:
        st.markdown("**Visitante**")
        a_score = away_form.get("form_score", 0.5)
        a_lbl, a_pct = _format_form_score(a_score)
        a_pts = away_form.get("avg_points_per_match", 0.0)
        a_sample = away_form.get("sample_size", 0)
        a_suff = away_form.get("sufficient", False)

        st.metric(
            label="Forma Reciente",
            value=a_lbl,
            delta=f"{a_pts:.1f} pts / partido",
            help="Rendimiento del equipo en sus últimos partidos ponderados por antigüedad (0% = racha negativa, 100% = racha perfecta)."
        )
        st.progress(a_pct / 100.0)

        # Motivación / Tendencia
        a_trend = away_mot.get("trend_score", 0.5)
        st.markdown(
            f"**Tendencia:** {_format_trend_score(a_trend)}",
            help="Compara el rendimiento de los partidos más recientes contra los anteriores para detectar si el equipo viene en alza o en baja."
        )
        if "recent_avg_points" in away_mot and "older_avg_points" in away_mot:
            st.caption(f"Últimos juegos: {away_mot['recent_avg_points']:.1f} pts vs Previos: {away_mot['older_avg_points']:.1f} pts")

        # Indicador de confianza amigable
        if a_suff:
            st.markdown(f"🟢 **Confianza Alta** `(Basado en {a_sample} partidos)`")
        else:
            st.markdown(f"🟡 **Confianza Limitada** `(Solo {a_sample} partido{'s' if a_sample != 1 else ''} evaluado{'s' if a_sample != 1 else ''})`")

    st.divider()

    # 3. Historial H2H
    st.markdown("##### Historial Directo (Enfrentamientos en esta sede)")
    h2h = context.get("head_to_head") or {}
    h2h_sample = h2h.get("sample_size", 0)
    h2h_suff = h2h.get("sufficient", False)

    if h2h_sample == 0 or (not h2h_suff and h2h_sample < 2):
        st.info("ℹ️ Sin historial directo registrado entre ambos equipos en esta sede.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Victorias Local", h2h.get("home_wins", 0), help="Victorias del local jugando en su estadio ante este rival.")
        with c2:
            st.metric("Empates", h2h.get("draws", 0), help="Empates registrados entre ambos en esta sede.")
        with c3:
            st.metric("Victorias Visitante", h2h.get("away_wins", 0), help="Victorias de la visita en este estadio.")
        with c4:
            g_home = h2h.get("avg_home_goals", 0.0)
            g_away = h2h.get("avg_away_goals", 0.0)
            st.metric("Goles promedio", f"{g_home:.1f} - {g_away:.1f}", help="Promedio de goles por partido entre ambos en esta sede.")

        if not h2h_suff:
            st.caption(f"Muestra reducida: Basado únicamente en {h2h_sample} enfrentamiento(s).")
        else:
            win_rate = h2h.get("home_win_rate", 0.0) * 100
            st.caption(f"Efectividad local en esta sede: {win_rate:.0f}% de victorias en {h2h_sample} partidos.")

    st.divider()

    # 4. Perfil del Árbitro
    st.markdown("##### Perfil Arbitral")
    ref = context.get("referee_profile") or {}
    ref_available = ref.get("available", False)
    ref_name = ref.get("referee_name")

    if not ref_available:
        if ref_name:
            st.info(f"ℹ️ Árbitro designado: **{ref_name}** (sin estadísticas históricas suficientes en la base de datos).")
        else:
            st.info("ℹ️ Árbitro por confirmar.")
    else:
        st.markdown(f"**Árbitro principal:** `{ref_name}`")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.metric(
                "Amarillas prom.",
                f"{ref.get('avg_yellow_cards_per_match', 0.0):.1f}",
                help="Promedio de tarjetas amarillas mostradas por partido."
            )
        with rc2:
            st.metric(
                "Rojas prom.",
                f"{ref.get('avg_red_cards_per_match', 0.0):.2f}",
                help="Promedio de tarjetas rojas mostradas por partido."
            )
        with rc3:
            st.metric(
                "Faltas prom.",
                f"{ref.get('avg_fouls_per_match', 0.0):.1f}",
                help="Promedio de faltas cobradas por partido."
            )
        ref_sample = ref.get("sample_size", 0)
        st.caption(f"Estadísticas calculadas sobre {ref_sample} partidos dirigidos registrados.")

        st.markdown(
            """
            <style>
            /* Achica el texto principal de st.metric para evitar que se corte */
            [data-testid="stMetricValue"] {
                font-size: 1.2rem !important; 
            }
            </style>
            """,
            unsafe_allow_html=True
        )