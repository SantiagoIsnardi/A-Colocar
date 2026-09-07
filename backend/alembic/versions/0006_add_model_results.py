"""add model_results table

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("prediction_id", sa.BigInteger(), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("value_bet_id", sa.BigInteger(), nullable=True),
        sa.Column("market", sa.String(50), nullable=False),
        sa.Column("line", sa.Numeric(5, 2), nullable=False),
        sa.Column("predicted_probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("actual_outcome", sa.Boolean(), nullable=False),
        sa.Column("brier_score", sa.Numeric(6, 5), nullable=False),
        sa.Column("closing_probability_implied", sa.Numeric(5, 4), nullable=True),
        sa.Column("clv_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], name="fk_model_results_prediction_id_predictions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_model_results_match_id_matches", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["value_bet_id"], ["value_bets.id"], name="fk_model_results_value_bet_id_value_bets", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_model_results"),
        sa.UniqueConstraint("prediction_id", name="uq_model_results_prediction_id"),
    )
    op.create_index("ix_model_results_version_date", "model_results", ["model_version", "resolved_at"])
    op.create_index("ix_model_results_market", "model_results", ["market"])


def downgrade() -> None:
    op.drop_index("ix_model_results_market", "model_results")
    op.drop_index("ix_model_results_version_date", "model_results")
    op.drop_table("model_results")