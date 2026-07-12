"""Calendar events (catalysts): FOMC, Beige Book, Fed stat releases.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("trust_level", sa.SmallInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("scheduled_on", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.String(length=32), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("provider_metadata", JSONB(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_calendar_event_identity",
        "calendar_events",
        ["source_id", "event_type", "scheduled_on", "title"],
        unique=True,
    )
    op.create_index("ix_calendar_events_scheduled_on", "calendar_events", ["scheduled_on"])


def downgrade() -> None:
    op.drop_table("calendar_events")
