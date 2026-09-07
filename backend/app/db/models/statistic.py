from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime,
    ForeignKey, Index, SmallInteger, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Statistic(Base):
    __tablename__ = "statistics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    goals: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    goals_conceded: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    corners: Mapped[int | None] = mapped_column(SmallInteger)
    yellow_cards: Mapped[int | None] = mapped_column(SmallInteger)
    red_cards: Mapped[int | None] = mapped_column(SmallInteger)
    fouls: Mapped[int | None] = mapped_column(SmallInteger)
    shots_total: Mapped[int | None] = mapped_column(SmallInteger)
    shots_on_target: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", name="uq_statistics_match_team"),
        CheckConstraint(
            "shots_on_target IS NULL OR shots_total IS NULL OR shots_on_target <= shots_total",
            name="ck_statistics_shots",
        ),
        Index("ix_statistics_team_id", "team_id"),
        Index("ix_statistics_match_id", "match_id"),
    )

    def __repr__(self) -> str:
        return f"<Statistic match={self.match_id} team={self.team_id}>"