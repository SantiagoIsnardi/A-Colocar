import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime,
    ForeignKey, Index, Numeric, String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class OddsSide(str, enum.Enum):
    over = "over"
    under = "under"


class Odds(Base):
    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    line: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    side: Mapped[OddsSide] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    is_closing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("price > 1.0", name="ck_odds_price_valid"),
        Index("ix_odds_match_market_line_side_date", "match_id", "market", "line", "side", "captured_at"),
        Index("ix_odds_closing", "match_id", "market", "line", "side", "is_closing"),
    )

    def __repr__(self) -> str:
        return f"<Odds match={self.match_id} {self.market} {self.line} {self.side} @{self.price}>"