"""Raw payloads, macro series catalog, and bitemporal macro observations.

``macro_observations`` becomes a TimescaleDB hypertable partitioned by
``observation_date``; its composite primary key includes the partition
column plus ``as_of`` so revisions coexist (ADR-004).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_payloads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("dataset", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_raw_payloads_provider_dataset_hash",
        "raw_payloads",
        ["provider", "dataset", "content_hash"],
        unique=True,
    )

    op.create_table(
        "macro_series",
        sa.Column("series_id", sa.String(length=128), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "macro_observations",
        sa.Column("series_id", sa.String(length=128), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("raw_payload_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("series_id", "observation_date", "as_of"),
        sa.ForeignKeyConstraint(["series_id"], ["macro_series.series_id"]),
        sa.ForeignKeyConstraint(["raw_payload_id"], ["raw_payloads.id"]),
    )
    op.create_index(
        "ix_macro_observations_series_date_asof",
        "macro_observations",
        ["series_id", "observation_date", "as_of"],
    )
    # Daily macro data → one-year chunks keep chunk counts sensible.
    op.execute(
        "SELECT create_hypertable("
        "'macro_observations', 'observation_date', "
        "chunk_time_interval => INTERVAL '1 year')"
    )


def downgrade() -> None:
    op.drop_table("macro_observations")
    op.drop_table("macro_series")
    op.drop_index("uq_raw_payloads_provider_dataset_hash", table_name="raw_payloads")
    op.drop_table("raw_payloads")
