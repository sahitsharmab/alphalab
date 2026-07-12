"""Storage models for evidence records and their entity links (ADR-013).

Evidence is permanent (insert-only) and never isolated: every record can
link to typed entities through ``evidence_entities`` — the relational seed
of the Evidence Graph.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Trust denormalized from the registry at ingestion time so queries and
    # future Decision Frameworks never need a code-level join (ADR-011).
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trust_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_payload_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw_payloads.id"))
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    entities: Mapped[list["EvidenceEntity"]] = relationship(
        back_populates="record", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        # One record per source-scoped external id (accession number, guid…).
        Index("uq_evidence_source_external", "source_id", "external_id", unique=True),
        Index("ix_evidence_published_at", "published_at"),
    )


class EvidenceEntity(Base):
    """One edge from an evidence record to a typed entity (ADR-013)."""

    __tablename__ = "evidence_entities"

    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"), primary_key=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    entity_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="subject")

    record: Mapped[EvidenceRecord] = relationship(back_populates="entities")

    __table_args__ = (
        Index("ix_evidence_entities_lookup", "entity_type", "entity_key", "evidence_id"),
    )
