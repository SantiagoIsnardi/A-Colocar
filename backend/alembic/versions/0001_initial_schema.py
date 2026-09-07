"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear enum con manejo de duplicado via SQL puro
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE match_status AS ENUM (
                'scheduled', 'live', 'finished', 'postponed', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.create_table(
        "teams",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="api_football"),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("short_name", sa.String(50), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("league", sa.String(150), nullable=True),
        sa.Column("founded_year", sa.SmallInteger(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
        sa.UniqueConstraint("source", "external_id", name="uq_teams_source_external_id"),
    )
    op.create_index("ix_teams_name", "teams", ["name"])
    op.create_index("ix_teams_country_league", "teams", ["country", "league"])

    # Status como String — evita que SQLAlchemy intente crear el enum de nuevo
    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="api_football"),
        sa.Column("home_team_id", sa.BigInteger(), nullable=False),
        sa.Column("away_team_id", sa.BigInteger(), nullable=False),
        sa.Column("league", sa.String(150), nullable=False),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(150), nullable=True),
        sa.Column("referee", sa.String(150), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("home_score", sa.SmallInteger(), nullable=True),
        sa.Column("away_score", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"], name="fk_matches_home_team_id_teams", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"], name="fk_matches_away_team_id_teams", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_matches"),
        sa.UniqueConstraint("source", "external_id", name="uq_matches_source_external_id"),
        sa.CheckConstraint("home_team_id != away_team_id", name="ck_matches_different_teams"),
    )
    op.create_index("ix_matches_home_team_date", "matches", ["home_team_id", "match_date"])
    op.create_index("ix_matches_away_team_date", "matches", ["away_team_id", "match_date"])

    # Convertir status a enum: primero quitar default, cambiar tipo, reponer default
    op.execute("ALTER TABLE matches ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE matches ALTER COLUMN status TYPE match_status USING status::match_status")
    op.execute("ALTER TABLE matches ALTER COLUMN status SET DEFAULT 'scheduled'")

def downgrade() -> None:
    op.drop_table("matches")
    op.drop_table("teams")
    sa.Enum(name="match_status").drop(op.get_bind(), checkfirst=True)