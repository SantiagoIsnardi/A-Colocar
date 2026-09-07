"""add value_bets table

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-05 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "value_bets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("prediction_id", sa.BigInteger(), nullable=False),
        sa.Column("odds_id", sa.BigInteger(), nullable=False),
        sa.Column("market", sa.String(50), nullable=False),
        sa.Column("line", sa.Numeric(5, 2), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("probability_model", sa.Numeric(5, 4), nullable=False),
        sa.Column("probability_implied", sa.Numeric(5, 4), nullable=False),
        sa.Column("edge", sa.Numeric(5, 4), nullable=False),
        sa.Column("expected_value", sa.Numeric(6, 4), nullable=False),
        sa.Column("kelly_stake_pct", sa.Numeric(5, 4), nullable=True),
        sa.Column("price", sa.Numeric(6, 3), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_value_bets_match_id_matches", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], name="fk_value_bets_prediction_id_predictions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["odds_id"], ["odds.id"], name="fk_value_bets_odds_id_odds", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_value_bets"),
        sa.CheckConstraint("edge > 0", name="ck_value_bets_positive_edge"),
    )
    op.create_index("ix_value_bets_match_id", "value_bets", ["match_id"])
    op.create_index("ix_value_bets_edge_open", "value_bets", ["edge", "status"])
    op.create_index("ix_value_bets_market_edge", "value_bets", ["market", "edge"])


def downgrade() -> None:
    op.drop_index("ix_value_bets_market_edge", "value_bets")
    op.drop_index("ix_value_bets_edge_open", "value_bets")
    op.drop_index("ix_value_bets_match_id", "value_bets")
    op.drop_table("value_bets")