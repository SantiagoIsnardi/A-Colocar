from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Index, Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ModelResult(Base):
    __tablename__ = "model_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    value_bet_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("value_bets.id", ondelete="SET NULL")
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    line: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    predicted_probability: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    actual_outcome: Mapped[bool] = mapped_column(Boolean, nullable=False)
    brier_score: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    closing_probability_implied: Mapped[float | None] = mapped_column(Numeric(5, 4))
    clv_pct: Mapped[float | None] = mapped_column(Numeric(6, 4))
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("prediction_id", name="uq_model_results_prediction_id"),
        Index("ix_model_results_version_date", "model_version", "resolved_at"),
        Index("ix_model_results_market", "market"),
    )

    def __repr__(self) -> str:
        return f"<ModelResult prediction={self.prediction_id} brier={self.brier_score}>"