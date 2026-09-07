"""
Mapea la respuesta de football-data.org al modelo interno Team/Match.
Usa source='football_data' para convivir sin conflicto con los registros
que ya vinieron de source='api_football'.
"""

from datetime import datetime

from app.db.models.match import Match, MatchStatus
from app.db.models.team import Team

_STATUS_MAP: dict[str, MatchStatus] = {
    "SCHEDULED": MatchStatus.scheduled,
    "TIMED": MatchStatus.scheduled,
    "IN_PLAY": MatchStatus.live,
    "PAUSED": MatchStatus.live,
    "FINISHED": MatchStatus.finished,
    "POSTPONED": MatchStatus.postponed,
    "SUSPENDED": MatchStatus.cancelled,
    "CANCELLED": MatchStatus.cancelled,
}


class FootballDataMapper:

    @staticmethod
    def team_from_api(team_data: dict) -> Team:
        return Team(
            external_id=str(team_data["id"]),
            source="football_data",
            name=team_data["name"],
            short_name=team_data.get("tla") or team_data.get("shortName"),
            country=(team_data.get("area") or {}).get("name"),
            logo_url=team_data.get("crest"),
        )

    @staticmethod
    def match_from_api(match_data: dict, home_team_id: int, away_team_id: int) -> Match:
        raw_status = match_data.get("status", "SCHEDULED")
        status = _STATUS_MAP.get(raw_status, MatchStatus.scheduled)

        raw_date = match_data.get("utcDate", "")
        match_date = (
            datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if raw_date
            else datetime.utcnow()
        )

        score = match_data.get("score", {}).get("fullTime", {})
        competition_name = match_data.get("competition", {}).get("name", "")
        season_info = match_data.get("season", {})
        season = str(season_info.get("startDate", ""))[:4] or "unknown"

        return Match(
            external_id=str(match_data["id"]),
            source="football_data",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league=competition_name,
            season=season,
            match_date=match_date,
            status=status,
            home_score=score.get("home"),
            away_score=score.get("away"),
        )