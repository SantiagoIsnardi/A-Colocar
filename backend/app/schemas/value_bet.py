from pydantic import BaseModel


class EvaluatedLine(BaseModel):
    line: float
    side: str
    price: float
    probability_model: float
    probability_implied: float
    edge: float
    expected_value: float
    persisted: bool
    value_bet_id: int | None = None
    kelly_stake_pct: float | None = None


class ValueFinderResponse(BaseModel):
    match_id: int
    market: str
    evaluated_lines: list[EvaluatedLine]
    value_bets_found: int


class ValueBetOut(BaseModel):
    id: int
    match_id: int
    market: str
    line: float
    side: str
    probability_model: float
    probability_implied: float
    edge: float
    expected_value: float
    kelly_stake_pct: float | None
    price: float
    status: str
    detected_at: str