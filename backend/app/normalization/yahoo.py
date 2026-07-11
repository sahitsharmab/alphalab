"""Normalizes Yahoo v8 chart JSON into instrument metadata + market bars.

Bar dates are computed in the exchange's own timezone (from chart meta) so
a bar is attributed to the trading day it describes, not the UTC day of
its epoch timestamp. Rows with missing closes (halts, partial data) are
skipped. Structural surprises fail loudly.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.normalization import NormalizationError
from app.schemas.market import InstrumentInfo, MarketBarIn


def _require(container: dict[str, Any], key: str, context: str) -> Any:
    if key not in container or container[key] is None:
        raise NormalizationError(f"yahoo chart: missing {key!r} in {context}")
    return container[key]


def parse_chart(payload_text: str) -> tuple[InstrumentInfo, list[MarketBarIn]]:
    """Parse one v8 chart response into (instrument, bars)."""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"yahoo chart: invalid JSON: {exc}") from exc

    chart = _require(payload, "chart", "payload")
    if chart.get("error"):
        raise NormalizationError(f"yahoo chart: provider error: {chart['error']}")
    results = _require(chart, "result", "chart")
    if not results:
        raise NormalizationError("yahoo chart: empty result")
    result = results[0]

    meta = _require(result, "meta", "result")
    symbol = str(_require(meta, "symbol", "meta")).upper()
    timezone = ZoneInfo(str(_require(meta, "exchangeTimezoneName", "meta")))
    instrument = InstrumentInfo(
        symbol=symbol,
        name=str(meta.get("longName") or meta.get("shortName") or symbol),
        currency=str(meta.get("currency") or ""),
        exchange=str(meta.get("fullExchangeName") or meta.get("exchangeName") or ""),
    )

    timestamps: list[int] = result.get("timestamp") or []
    if not timestamps:
        return instrument, []

    indicators = _require(result, "indicators", "result")
    quote = _require(indicators, "quote", "indicators")[0]
    adjclose_blocks = indicators.get("adjclose") or [{}]
    adjcloses = adjclose_blocks[0].get("adjclose") or [None] * len(timestamps)

    def series(name: str) -> list[Any]:
        return quote.get(name) or [None] * len(timestamps)

    opens, highs, lows, closes, volumes = (
        series("open"),
        series("high"),
        series("low"),
        series("close"),
        series("volume"),
    )

    bars: list[MarketBarIn] = []
    for i, ts in enumerate(timestamps):
        close = closes[i]
        if close is None:
            continue  # halted/partial rows carry no usable bar
        bar_date = datetime.fromtimestamp(ts, tz=timezone).date()
        adj = adjcloses[i] if adjcloses[i] is not None else close
        bars.append(
            MarketBarIn(
                symbol=symbol,
                bar_date=bar_date,
                open=_decimal(opens[i], close),
                high=_decimal(highs[i], close),
                low=_decimal(lows[i], close),
                close=_decimal(close, close),
                adj_close=_decimal(adj, close),
                volume=int(volumes[i] or 0),
            )
        )
    return instrument, bars


def _decimal(value: Any, fallback: Any) -> Decimal:
    """Convert a Yahoo float to Decimal via str (no binary-float artifacts)."""
    raw = value if value is not None else fallback
    return Decimal(str(raw))
