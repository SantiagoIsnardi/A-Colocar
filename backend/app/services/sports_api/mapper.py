from datetime import datetime

from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic
from app.db.models.team import Team

_STATUS_MAP: dict[str, MatchStatus] = {
    "FT": MatchStatus.finished,
    "AET": MatchStatus.finished,
    "PEN": MatchStatus.finished,
    "NS": MatchStatus.scheduled,
    "TBD": MatchStatus.scheduled,
    "1H": MatchStatus.live,
    "HT": MatchStatus.live,
    "2H": MatchStatus.live,
    "ET": MatchStatus.live,
    "BT": MatchStatus.live,
    "LIVE": MatchStatus.live,
    "PST": MatchStatus.postponed,
    "CANC": MatchStatus.cancelled,
    "ABD": MatchStatus.cancelled,
    "SUSP": MatchStatus.cancelled,
}


class APIFootballMapper:

    @staticmethod
    def team_from_api(data: dict) -> Team:
        t = data.get("team", data)
        return Team(
            external_id=str(t["id"]),
            source="api_football",
            name=t["name"],
            short_name=t.get("code"),
            country=t.get("country"),
            logo_url=t.get("logo"),
            founded_year=t.get("founded"),
        )

    @staticmethod
    def match_from_fixture(fixture: dict, home_team_id: int, away_team_id: int) -> Match:
        f = fixture["fixture"]
        league = fixture["league"]
        goals = fixture.get("goals", {})

        raw_status = f.get("status", {}).get("short", "NS")
        status = _STATUS_MAP.get(raw_status, MatchStatus.scheduled)

        raw_date = f.get("date", "")
        match_date = (
            datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if raw_date
            else datetime.utcnow()
        )

        return Match(
            external_id=str(f["id"]),
            source="api_football",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league=league.get("name", ""),
            season=str(league.get("season", "")),
            match_date=match_date,
            venue=f.get("venue", {}).get("name"),
            referee=f.get("referee"),
            status=status,
            home_score=goals.get("home"),
            away_score=goals.get("away"),
        )

    @staticmethod
    def statistic_from_fixture_stats(
        team_stats: dict,
        match_id: int,
        team_id: int,
        is_home: bool,
        goals: int,
        goals_conceded: int,
    ) -> Statistic:
        """
        Mapea la respuesta de /fixtures/statistics para un equipo
        al modelo Statistic interno.
        """
        stats_list = team_stats.get("statistics", [])
        stats_map = {s["type"]: s["value"] for s in stats_list}

        def to_int(key: str) -> int | None:
            val = stats_map.get(key)
            if val is None or val == "" or val == "N/A":
                return None
            if isinstance(val, str) and val.endswith("%"):
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        return Statistic(
            match_id=match_id,
            team_id=team_id,
            is_home=is_home,
            goals=goals,
            goals_conceded=goals_conceded,
            corners=to_int("Corner Kicks"),
            yellow_cards=to_int("Yellow Cards"),
            red_cards=to_int("Red Cards"),
            fouls=to_int("Fouls"),
            shots_total=to_int("Total Shots"),
            shots_on_target=to_int("Shots on Goal"),
        )