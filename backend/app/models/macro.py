"""Storage models for raw payloads and bitemporal macro observations.

Raw data is immutable: ``RawPayload`` rows are only ever inserted, never
updated (PROJECT.md Data Philosophy). ``MacroObservation`` is bitemporal
(ADR-004): revisions are new rows with a newer ``as_of``; nothing is
updated in place.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RawPayload(Base):
    """An immutable raw response retrieved by a connector."""

    __tablename__ = "raw_payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # The same content for the same dataset is stored exactly once.
        Index(
            "uq_raw_payloads_provider_dataset_hash",
            "provider",
            "dataset",
            "content_hash",
            unique=True,
        ),
    )


class MacroSeries(Base):
    """Catalog of macro time series known to the platform."""

    __tablename__ = "macro_series"

    series_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MacroObservation(Base):
    """One bitemporal macro observation (TimescaleDB hypertable).

    Primary key includes ``observation_date`` (the hypertable partition
    column) and ``as_of``, so revisions of the same observation coexist.
    """

    __tablename__ = "macro_observations"

    series_id: Mapped[str] = mapped_column(ForeignKey("macro_series.series_id"), primary_key=True)
    observation_date: Mapped[date] = mapped_column(Date, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    raw_payload_id: Mapped[int | None] = mapped_column(ForeignKey("raw_payloads.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_macro_observations_series_date_asof", "series_id", "observation_date", "as_of"),
    )
