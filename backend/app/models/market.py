"""Storage models for instruments and bitemporal market bars (ADR-004)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Instrument(Base):
    """Catalog of instruments known to the platform."""

    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    exchange: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # SEC Central Index Key, zero-padded to 10 digits (set by the EDGAR connector).
    cik: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketBar(Base):
    """One bitemporal daily OHLCV bar (TimescaleDB hypertable).

    Adjusted closes are rewritten by splits/dividends; the ``as_of``
    dimension preserves what was known when (ADR-004).
    """

    __tablename__ = "market_bars"

    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"), primary_key=True)
    bar_date: Mapped[date] = mapped_column(Date, primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    adj_close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    raw_payload_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw_payloads.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_market_bars_symbol_date_asof", "symbol", "bar_date", "as_of"),)
