"""add statistics table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "statistics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.BigInteger(), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("goals", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("goals_conceded", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("corners", sa.SmallInteger(), nullable=True),
        sa.Column("yellow_cards", sa.SmallInteger(), nullable=True),
        sa.Column("red_cards", sa.SmallInteger(), nullable=True),
        sa.Column("fouls", sa.SmallInteger(), nullable=True),
        sa.Column("shots_total", sa.SmallInteger(), nullable=True),
        sa.Column("shots_on_target", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_statistics_match_id_matches", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_statistics_team_id_teams", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_statistics"),
        sa.UniqueConstraint("match_id", "team_id", name="uq_statistics_match_team"),
        sa.CheckConstraint(
            "shots_on_target IS NULL OR shots_total IS NULL OR shots_on_target <= shots_total",
            name="ck_statistics_shots",
        ),
    )
    op.create_index("ix_statistics_team_id", "statistics", ["team_id"])
    op.create_index("ix_statistics_match_id", "statistics", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_statistics_match_id", "statistics")
    op.drop_index("ix_statistics_team_id", "statistics")
    op.drop_table("statistics")