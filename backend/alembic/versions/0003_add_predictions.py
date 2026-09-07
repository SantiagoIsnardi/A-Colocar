"""add predictions table

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("market", sa.String(50), nullable=False),
        sa.Column("line", sa.Numeric(5, 2), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("probability_over", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("sample_size", sa.SmallInteger(), nullable=True),
        sa.Column("model_params", postgresql.JSONB(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_predictions_match_id_matches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
        sa.CheckConstraint(
            "probability_over >= 0 AND probability_over <= 1",
            name="ck_predictions_probability_range",
        ),
    )
    op.create_index(
        "ix_predictions_match_market_line_date",
        "predictions",
        ["match_id", "market", "line", "computed_at"],
    )
    op.create_index("ix_predictions_model_version", "predictions", ["model_version"])


def downgrade() -> None:
    op.drop_index("ix_predictions_model_version", "predictions")
    op.drop_index("ix_predictions_match_market_line_date", "predictions")
    op.drop_table("predictions")