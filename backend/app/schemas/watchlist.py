"""Contracts for a single-user, user-curated momentum watchlist."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1, max_length=16)
    note: str = Field(default="", max_length=500)


class WatchlistItemOut(BaseModel):
    symbol: str
    note: str
    added_at: datetime


class WatchlistOverviewRow(BaseModel):
    symbol: str
    name: str
    price: float
    price_date: date
    change_1d: float | None
    return_1w: float | None
    return_1m: float | None
    ema9_distance: float | None
    ema21_distance: float | None
    relative_1m_spy: float | None
    relative_1m_qqq: float | None
    note: str
