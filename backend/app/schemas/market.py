"""Domain schemas for market data (bitemporal, ADR-004)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InstrumentInfo(BaseModel):
    """Descriptive metadata for one tradable instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    currency: str
    exchange: str


class MarketBarIn(BaseModel):
    """A normalized daily OHLCV bar ready for bitemporal storage."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    bar_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int


class MarketBarOut(BaseModel):
    """A bar as served to consumers (features, engines, API)."""

    symbol: str
    bar_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int
