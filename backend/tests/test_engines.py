"""Unit tests for the Technical and Inflation engines.

The engines' contract (ADR-010): statements + evidence, every cited
evidence id resolvable — the WorkspaceSection validator enforces this, so
constructing a section at all is already a traceability test.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.engines.inflation import build_macro_section
from app.engines.relative import build_relative_section
from app.engines.technical import build_historical_section, build_technical_section
from app.schemas.macro import MacroObservationOut
from tests.helpers import make_bars


def rising_closes(n: int = 300) -> list[float]:
    return [100.0 * (1.002**i) for i in range(n)]


def varying_closes(n: int = 300, scale: float = 1.0, start: float = 100.0) -> list[float]:
    """Upward-drifting series with VARYING returns (beta needs variance)."""
    pattern = [0.012, -0.004, 0.008, -0.002]
    closes = [start]
    for i in range(1, n):
        closes.append(closes[-1] * (1 + scale * pattern[i % len(pattern)]))
    return closes


def test_technical_section_uptrend() -> None:
    section = build_technical_section("TST", make_bars("TST", rising_closes()))

    assert section.id == "technical"
    texts = " ".join(s.text for s in section.statements)
    assert "uptrend" in texts.lower()
    evidence_ids = {e.id for e in section.evidence}
    assert {"last_close", "ema9", "ema21", "ema50", "ema200", "rsi14"} <= evidence_ids
    assert "1-5 day momentum read" in texts


def test_technical_section_degrades_on_short_history() -> None:
    section = build_technical_section("TST", make_bars("TST", [100.0] * 10))
    assert any("not enough price history" in s.text.lower() for s in section.statements)


def test_historical_section_has_returns_drawdown_beta() -> None:
    # Asset amplifies the benchmark's (varying) daily returns 2x → beta ≈ 2.
    bars = make_bars("TST", varying_closes(300, scale=2.0))
    bench = make_bars("SPY", varying_closes(300, scale=1.0, start=400.0))

    section = build_historical_section("TST", bars, "SPY", bench)

    evidence_ids = {e.id for e in section.evidence}
    assert {"ret_6m", "ret_1y", "mdd_1y", "range_pos", "beta_1y"} <= evidence_ids
    beta_item = next(e for e in section.evidence if e.id == "beta_1y")
    assert beta_item.value is not None
    assert beta_item.value > 1.5


def test_relative_section_labels_etf_proxies_and_resolves_evidence() -> None:
    asset = make_bars("TST", [100.0 * (1.01**i) for i in range(80)])
    spy = make_bars("SPY", [400.0 * (1.002**i) for i in range(80)])
    qqq = make_bars("QQQ", [300.0 * (1.004**i) for i in range(80)])

    section = build_relative_section("TST", asset, {"SPY": spy, "QQQ": qqq})

    texts = " ".join(statement.text for statement in section.statements)
    assert "SPY (S&P 500 ETF proxy)" in texts
    assert "QQQ (Nasdaq-100 ETF proxy)" in texts
    assert "Sector and peer comparison: not shown" in texts
    evidence_ids = {item.id for item in section.evidence}
    assert {"rel_1w_spy", "rel_1m_spy", "rel_3m_spy"} <= evidence_ids


def _yoy(values: list[tuple[str, str]]) -> list[MacroObservationOut]:
    return [
        MacroObservationOut(
            series_id="nowflation.headline.yoy",
            observation_date=date.fromisoformat(d),
            as_of=datetime(2026, 7, 12, tzinfo=UTC),
            value=Decimal(v),
        )
        for d, v in values
    ]


def test_macro_section_low_and_falling() -> None:
    observations = _yoy([("2026-04-01", "0.0250"), ("2026-07-01", "0.0178")])

    section = build_macro_section(observations)

    texts = " ".join(s.text for s in section.statements).lower()
    assert "regime is low" in texts
    assert "falling" in texts
    assert {"yoy_now", "yoy_3m_ago", "yoy_3m_change"} <= {e.id for e in section.evidence}


def test_macro_section_high_and_rising() -> None:
    observations = _yoy([("2026-04-01", "0.0400"), ("2026-07-01", "0.0480")])
    texts = " ".join(s.text for s in build_macro_section(observations).statements).lower()
    assert "regime is high" in texts
    assert "rising" in texts


def test_macro_section_empty_data() -> None:
    section = build_macro_section([])
    assert any("no inflation data" in s.text.lower() for s in section.statements)
