import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey,
    Index, Numeric, SmallInteger, String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConfidenceLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    line: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    probability_over: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        String(20), nullable=False, server_default=ConfidenceLevel.medium.value
    )
    sample_size: Mapped[int | None] = mapped_column(SmallInteger)
    model_params: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "probability_over >= 0 AND probability_over <= 1",
            name="ck_predictions_probability_range",
        ),
        Index("ix_predictions_match_market_line_date", "match_id", "market", "line", "computed_at"),
        Index("ix_predictions_model_version", "model_version"),
    )

    def __repr__(self) -> str:
        return f"<Prediction match={self.match_id} {self.market} {self.line} p={self.probability_over}>"