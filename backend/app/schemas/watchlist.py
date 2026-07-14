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


class BoardLevel(BaseModel):
    """One EMA level relative to the current price."""

    model_config = ConfigDict(frozen=True)

    label: str  # e.g. "200-EMA"
    value: float
    distance: float  # signed fraction from price: (value/price - 1)


class DecisionBoardRow(BaseModel):
    """A watchlist name as a decision-ready row: role + levels + context."""

    symbol: str
    name: str
    price: float
    price_date: date
    role: str  # beta band: Hedge | Defensive | Core | High-beta | Very high-beta
    beta: float | None  # 1-year beta vs SPY
    change_1d: float | None
    return_1w: float | None
    return_1m: float | None
    relative_1m_spy: float | None
    support: BoardLevel | None  # nearest EMA below price
    resistance: BoardLevel | None  # nearest EMA above price
    has_risk_plan: bool
    note: str


class DecisionBoard(BaseModel):
    """The whole board: rows plus the next shared market catalyst."""

    generated_at: datetime
    next_catalyst: str | None  # e.g. "CPI — 2026-07-14 (tomorrow)"
    rows: list[DecisionBoardRow]
