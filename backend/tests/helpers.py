"""Test data builders shared across suites."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.schemas.market import MarketBarOut


def make_bars(
    symbol: str,
    closes: list[float],
    end: datetime | None = None,
) -> list[MarketBarOut]:
    """Daily bars ending today (calendar days; fine for feature tests)."""
    end = end or datetime.now(UTC)
    n = len(closes)
    bars = []
    for i, close in enumerate(closes):
        day = (end - timedelta(days=n - 1 - i)).date()
        value = Decimal(str(round(close, 6)))
        bars.append(
            MarketBarOut(
                symbol=symbol,
                bar_date=day,
                open=value,
                high=value * Decimal("1.01"),
                low=value * Decimal("0.99"),
                close=value,
                adj_close=value,
                volume=1_000_000,
            )
        )
    return bars


def make_yahoo_chart_json(
    symbol: str,
    closes: list[float],
    name: str = "Test Corp",
    end: datetime | None = None,
) -> str:
    """A minimal Yahoo v8 chart payload with daily bars ending today."""
    end = end or datetime.now(UTC)
    # Yahoo daily bars are timestamped during/after the exchange session.
    # Pin synthetic bars to 16:00 UTC so a DST transition cannot map two
    # consecutive UTC midnights onto the same New York calendar date.
    end = end.replace(hour=16, minute=0, second=0, microsecond=0)
    n = len(closes)
    timestamps = [int((end - timedelta(days=n - 1 - i)).timestamp()) for i in range(n)]
    return json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": symbol,
                            "exchangeName": "NMS",
                            "fullExchangeName": "NasdaqGS",
                            "longName": name,
                            "exchangeTimezoneName": "America/New_York",
                        },
                        "timestamp": timestamps,
                        "indicators": {
                            "quote": [
                                {
                                    "open": closes,
                                    "high": [c * 1.01 for c in closes],
                                    "low": [c * 0.99 for c in closes],
                                    "close": closes,
                                    "volume": [1_000_000] * n,
                                }
                            ],
                            "adjclose": [{"adjclose": closes}],
                        },
                    }
                ],
                "error": None,
            }
        }
    )
