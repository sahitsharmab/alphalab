"""Technical feature functions over daily bar series.

All functions are pure and operate on plain float sequences ordered oldest
→ newest (adjusted closes unless stated otherwise). Insufficient history
returns ``None`` rather than a misleading number — engines degrade
gracefully by omitting the statement.

FEATURE_VERSION participates in experiment manifests (ADR-005): bump it on
any change to a computation.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any

FEATURE_VERSION = "1.0.0"

TRADING_DAYS_PER_YEAR = 252


def window_return(closes: Sequence[float], days: int) -> float | None:
    """Fractional return over the last ``days`` trading days."""
    if len(closes) <= days or closes[-1 - days] == 0:
        return None
    return closes[-1] / closes[-1 - days] - 1


def daily_returns(closes: Sequence[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1] != 0]


def ema(closes: Sequence[float], span: int) -> float | None:
    """Exponential moving average (standard smoothing 2/(span+1))."""
    if len(closes) < span:
        return None
    alpha = 2 / (span + 1)
    value = sum(closes[:span]) / span  # seed with SMA of the first window
    for close in closes[span:]:
        value = alpha * close + (1 - alpha) * value
    return value


def rsi(closes: Sequence[float], period: int = 14) -> float | None:
    """Relative Strength Index with Wilder smoothing."""
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def atr_fraction(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    """Average True Range (Wilder) as a fraction of the last close."""
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n or closes[-1] == 0:
        return None
    true_ranges = [
        max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        for i in range(1, n)
    ]
    value = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        value = (value * (period - 1) + tr) / period
    return value / closes[-1]


def realized_volatility(closes: Sequence[float], window: int = 20) -> float | None:
    """Annualized standard deviation of daily returns over ``window`` days."""
    returns = daily_returns(closes)
    if len(returns) < window:
        return None
    sample = returns[-window:]
    mean = sum(sample) / window
    variance = sum((r - mean) ** 2 for r in sample) / (window - 1)
    return math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR)


def max_drawdown(closes: Sequence[float], window: int = TRADING_DAYS_PER_YEAR) -> float | None:
    """Worst peak-to-trough decline (fraction ≤ 0) over the last ``window`` days."""
    sample = list(closes[-window:])
    if len(sample) < 2:
        return None
    peak = sample[0]
    worst = 0.0
    for close in sample:
        peak = max(peak, close)
        if peak > 0:
            worst = min(worst, close / peak - 1)
    return worst


def range_position(closes: Sequence[float], window: int = TRADING_DAYS_PER_YEAR) -> float | None:
    """Where the last close sits in its trailing range: 0 = low, 1 = high."""
    sample = list(closes[-window:])
    if len(sample) < 2:
        return None
    low, high = min(sample), max(sample)
    if high == low:
        return None
    return (sample[-1] - low) / (high - low)


def relative_volume(volumes: Sequence[float], window: int = 20) -> float | None:
    """Last day's volume relative to the average of the prior ``window`` days."""
    if len(volumes) < window + 1:
        return None
    baseline = sum(volumes[-window - 1 : -1]) / window
    if baseline == 0:
        return None
    return volumes[-1] / baseline


def beta(
    asset_closes_by_date: Mapping[Any, float],
    benchmark_closes_by_date: Mapping[Any, float],
    window: int = TRADING_DAYS_PER_YEAR,
) -> float | None:
    """OLS beta of asset daily returns vs benchmark, on shared dates only.

    Keys must be mutually sortable (dates in production, ints in tests).
    """
    shared = sorted(set(asset_closes_by_date) & set(benchmark_closes_by_date))
    if len(shared) < window // 2:  # demand at least half a window of overlap
        return None
    shared = shared[-(window + 1) :]
    asset = [asset_closes_by_date[d] for d in shared]
    bench = [benchmark_closes_by_date[d] for d in shared]
    asset_returns = daily_returns(asset)
    bench_returns = daily_returns(bench)
    n = min(len(asset_returns), len(bench_returns))
    if n < 2:
        return None
    asset_returns, bench_returns = asset_returns[-n:], bench_returns[-n:]
    mean_a = sum(asset_returns) / n
    mean_b = sum(bench_returns) / n
    covariance = sum((asset_returns[i] - mean_a) * (bench_returns[i] - mean_b) for i in range(n))
    variance = sum((r - mean_b) ** 2 for r in bench_returns)
    if variance == 0:
        return None
    return covariance / variance
