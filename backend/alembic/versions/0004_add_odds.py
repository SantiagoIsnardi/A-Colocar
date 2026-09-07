"""add odds table

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "odds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("bookmaker", sa.String(100), nullable=False),
        sa.Column("market", sa.String(50), nullable=False),
        sa.Column("line", sa.Numeric(5, 2), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("price", sa.Numeric(6, 3), nullable=False),
        sa.Column("is_closing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_odds_match_id_matches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_odds"),
        sa.CheckConstraint("price > 1.0", name="ck_odds_price_valid"),
    )
    op.create_index(
        "ix_odds_match_market_line_side_date",
        "odds",
        ["match_id", "market", "line", "side", "captured_at"],
    )
    op.create_index(
        "ix_odds_closing",
        "odds",
        ["match_id", "market", "line", "side", "is_closing"],
    )


def downgrade() -> None:
    op.drop_index("ix_odds_closing", "odds")
    op.drop_index("ix_odds_match_market_line_side_date", "odds")
    op.drop_table("odds")