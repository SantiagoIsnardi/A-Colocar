from pydantic import BaseModel


class GoalLinePrediction(BaseModel):
    line: float
    label: str
    probability_over: float
    percentage: float


class PredictionResponse(BaseModel):
    match_id: int
    model_version: str
    confidence_level: str
    sample_size: int
    lambda_home: float
    lambda_away: float
    predictions: list[GoalLinePrediction]