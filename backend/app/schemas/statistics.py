from pydantic import BaseModel


class MetricStats(BaseModel):
    mean: float
    std: float
    min: int
    max: int
    median: float
    sample_size: int


class TeamStatsResponse(BaseModel):
    team_id: int
    sample_size: int
    last_n_requested: int
    goals_scored: MetricStats | None = None
    goals_conceded: MetricStats | None = None
    corners: MetricStats | None = None
    yellow_cards: MetricStats | None = None
    red_cards: MetricStats | None = None
    fouls: MetricStats | None = None
    shots_total: MetricStats | None = None
    shots_on_target: MetricStats | None = None


class MatchTotalsResponse(BaseModel):
    team_id: int
    matches_analyzed: int
    total_goals: MetricStats | None = None
    total_corners: MetricStats | None = None
    total_yellow_cards: MetricStats | None = None
    total_fouls: MetricStats | None = None
    total_shots: MetricStats | None = None


class LineResult(BaseModel):
    frequency: float
    percentage: float
    count_over: int
    count_under_or_equal: int
    sample_size: int
    label: str


class FrequencyResponse(BaseModel):
    team_id: int
    matches_analyzed: int
    markets: dict[str, dict[str, LineResult]]