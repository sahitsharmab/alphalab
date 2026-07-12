"""Add permanent user risk plans.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("account_size", sa.Numeric(20, 4), nullable=False),
        sa.Column("entry", sa.Numeric(20, 6), nullable=False),
        sa.Column("invalidation", sa.Numeric(20, 6), nullable=False),
        sa.Column("target", sa.Numeric(20, 6), nullable=False),
        sa.Column("max_dollar_risk", sa.Numeric(20, 4), nullable=False),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_risk_plans_symbol", "risk_plans", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_risk_plans_symbol", table_name="risk_plans")
    op.drop_table("risk_plans")
