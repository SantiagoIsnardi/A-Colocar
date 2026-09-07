from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="api_football")
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    league: Mapped[str | None] = mapped_column(String(150))
    founded_year: Mapped[int | None] = mapped_column(SmallInteger)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_teams_source_external_id"),
        Index("ix_teams_country_league", "country", "league"),
        Index("ix_teams_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name!r}>"