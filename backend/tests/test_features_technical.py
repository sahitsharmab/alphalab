"""Unit tests for technical feature functions (known-value cases)."""

import math

from app.features import technical as ft


def test_window_return_exact() -> None:
    closes = [100.0, 105.0, 110.0]
    result = ft.window_return(closes, 2)
    assert result is not None
    assert math.isclose(result, 0.10)
    assert ft.window_return(closes, 5) is None  # insufficient history


def test_ema_of_constant_series_is_the_constant() -> None:
    assert ft.ema([50.0] * 60, span=20) == 50.0


def test_rsi_extremes() -> None:
    rising = [float(i) for i in range(1, 40)]
    falling = [float(i) for i in range(40, 1, -1)]
    assert ft.rsi(rising, 14) == 100.0
    assert ft.rsi(falling, 14) == 0.0
    assert ft.rsi([1.0, 2.0], 14) is None


def test_realized_volatility_of_constant_returns_is_zero() -> None:
    # 1% growth every day → zero variance of returns.
    closes = [100.0 * (1.01**i) for i in range(30)]
    vol = ft.realized_volatility(closes, 20)
    assert vol is not None
    assert vol < 1e-9


def test_max_drawdown_monotonic_rise_is_zero() -> None:
    closes = [float(i) for i in range(100, 160)]
    assert ft.max_drawdown(closes) == 0.0


def test_max_drawdown_known_decline() -> None:
    closes = [100.0, 120.0, 90.0, 110.0]
    dd = ft.max_drawdown(closes)
    assert dd is not None
    assert math.isclose(dd, 90.0 / 120.0 - 1)  # -25%


def test_range_position_bounds() -> None:
    closes = [10.0, 20.0, 15.0]
    assert ft.range_position(closes) == 0.5
    assert ft.range_position([5.0] * 10) is None  # degenerate range


def test_relative_volume() -> None:
    volumes = [100.0] * 20 + [300.0]
    assert ft.relative_volume(volumes, 20) == 3.0


def test_beta_of_scaled_series_matches_scale() -> None:
    # Asset return = 2 x benchmark return each day → beta 2. The benchmark
    # returns must VARY: constant returns have zero variance and beta is
    # numerically undefined.
    pattern = [0.01, -0.005, 0.007, -0.002]
    bench: dict[int, float] = {}
    asset: dict[int, float] = {}
    bench_value = asset_value = 100.0
    for day in range(300):
        if day > 0:
            r = pattern[day % len(pattern)]
            bench_value *= 1 + r
            asset_value *= 1 + 2 * r
        bench[day] = bench_value
        asset[day] = asset_value
    b = ft.beta(asset, bench, window=252)
    assert b is not None
    assert math.isclose(b, 2.0, rel_tol=1e-9)


def test_beta_requires_overlap() -> None:
    assert ft.beta({1: 10.0}, {2: 10.0}) is None
