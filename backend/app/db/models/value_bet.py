import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey,
    Index, Numeric, String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class BetStatus(str, enum.Enum):
    open = "open"
    won = "won"
    lost = "lost"
    void = "void"
    pushed = "pushed"


class ValueBet(Base):
    __tablename__ = "value_bets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    prediction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("predictions.id", ondelete="RESTRICT"), nullable=False
    )
    odds_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("odds.id", ondelete="RESTRICT"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    line: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    probability_model: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    probability_implied: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    edge: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    expected_value: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    kelly_stake_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    price: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    status: Mapped[BetStatus] = mapped_column(String(10), nullable=False, server_default=BetStatus.open.value)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("edge > 0", name="ck_value_bets_positive_edge"),
        Index("ix_value_bets_match_id", "match_id"),
        Index("ix_value_bets_edge_open", "edge", "status"),
        Index("ix_value_bets_market_edge", "market", "edge"),
    )

    def __repr__(self) -> str:
        return f"<ValueBet match={self.match_id} {self.market} {self.line} edge={self.edge}>"