"""
Mapea el DataFrame de estadísticas de Sofascore (scrape_team_match_stats)
al modelo interno Statistic.

Detalle crítico: Sofascore devuelve cada estadística repetida por período
(partido completo, 1er tiempo, 2do tiempo) — hay que filtrar por
period == 'ALL' para no sumar el partido completo más las mitades.
"""

import pandas as pd

from app.db.models.statistic import Statistic

_STAT_NAME_MAP: dict[str, str] = {
    "Corner kicks": "corners",
    "Yellow cards": "yellow_cards",
    "Fouls": "fouls",
    "Total shots": "shots_total",
    "Shots on target": "shots_on_target",
}


class SofascoreMapper:

    @staticmethod
    def _extract_full_match_stats(stats_df: pd.DataFrame) -> dict[str, dict[str, int]]:
        """
        Filtra el DataFrame a solo las filas del partido completo (period='ALL')
        y devuelve {campo_interno: {'home': valor, 'away': valor}}.
        """
        full_match = stats_df[stats_df["period"] == "ALL"]

        result: dict[str, dict[str, int]] = {}
        for _, row in full_match.iterrows():
            stat_name = row["name"]
            internal_field = _STAT_NAME_MAP.get(stat_name)
            if not internal_field:
                continue

            try:
                home_val = int(row["home"])
                away_val = int(row["away"])
            except (ValueError, TypeError):
                # Algunos valores vienen como "68%" o "104.5 km" — no aplican
                # a los campos numéricos que necesitamos (corners, tarjetas, etc.)
                continue

            result[internal_field] = {"home": home_val, "away": away_val}

        return result

    @classmethod
    def statistics_from_match(
        cls,
        stats_df: pd.DataFrame,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        home_goals: int,
        away_goals: int,
    ) -> list[Statistic]:
        """
        Devuelve dos objetos Statistic (uno por equipo) listos para persistir,
        a partir del DataFrame crudo de Sofascore.
        """
        extracted = cls._extract_full_match_stats(stats_df)

        def _get(field: str, side: str) -> int | None:
            entry = extracted.get(field)
            return entry[side] if entry else None

        home_stat = Statistic(
            match_id=match_id,
            team_id=home_team_id,
            is_home=True,
            goals=home_goals,
            goals_conceded=away_goals,
            corners=_get("corners", "home"),
            yellow_cards=_get("yellow_cards", "home"),
            fouls=_get("fouls", "home"),
            shots_total=_get("shots_total", "home"),
            shots_on_target=_get("shots_on_target", "home"),
        )

        away_stat = Statistic(
            match_id=match_id,
            team_id=away_team_id,
            is_home=False,
            goals=away_goals,
            goals_conceded=home_goals,
            corners=_get("corners", "away"),
            yellow_cards=_get("yellow_cards", "away"),
            fouls=_get("fouls", "away"),
            shots_total=_get("shots_total", "away"),
            shots_on_target=_get("shots_on_target", "away"),
        )

        return [home_stat, away_stat]