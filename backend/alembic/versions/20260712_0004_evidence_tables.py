"""Evidence records, entity links (Evidence Graph seed), instruments.cik.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("trust_level", sa.SmallInteger(), nullable=False),
        sa.Column("external_id", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_payload_id", sa.Integer(), sa.ForeignKey("raw_payloads.id"), nullable=True),
        sa.Column("provider_metadata", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_evidence_source_external",
        "evidence_records",
        ["source_id", "external_id"],
        unique=True,
    )
    op.create_index("ix_evidence_published_at", "evidence_records", ["published_at"])

    op.create_table(
        "evidence_entities",
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("evidence_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_key", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id", "entity_type", "entity_key"),
    )
    op.create_index(
        "ix_evidence_entities_lookup",
        "evidence_entities",
        ["entity_type", "entity_key", "evidence_id"],
    )

    # SEC CIK on the instrument catalog (filled by the EDGAR connector).
    op.add_column("instruments", sa.Column("cik", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("instruments", "cik")
    op.drop_table("evidence_entities")
    op.drop_table("evidence_records")
