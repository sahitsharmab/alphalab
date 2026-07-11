"""Instruments, bitemporal market bars (hypertable), workspace snapshots.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("symbol", sa.String(length=16), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "market_bars",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("bar_date", sa.Date(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("adj_close", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("raw_payload_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("symbol", "bar_date", "as_of"),
        sa.ForeignKeyConstraint(["symbol"], ["instruments.symbol"]),
        sa.ForeignKeyConstraint(["raw_payload_id"], ["raw_payloads.id"]),
    )
    op.create_index(
        "ix_market_bars_symbol_date_asof",
        "market_bars",
        ["symbol", "bar_date", "as_of"],
    )
    op.execute(
        "SELECT create_hypertable("
        "'market_bars', 'bar_date', chunk_time_interval => INTERVAL '1 year')"
    )

    op.create_table(
        "workspace_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workspace_snapshots_symbol", "workspace_snapshots", ["symbol"])


def downgrade() -> None:
    op.drop_table("workspace_snapshots")
    op.drop_table("market_bars")
    op.drop_table("instruments")
