"""Relative Context Engine: the stock vs market/growth proxies (M2, ADR-015).

Answers "is this stock leading or lagging?" over 1-week, 1-month, and
3-month windows against index ETF proxies — deterministic, computed on
shared trading dates. Proxies are named as proxies (ADR-016 guardrail);
sector/peer comparison is an honest gap until SIC mapping (task C4) ships.
"""

from app.features import technical as ft
from app.schemas.market import MarketBarOut
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

#: (window in trading days, human label, evidence-id suffix)
WINDOWS: tuple[tuple[int, str, str], ...] = (
    (5, "1-week", "1w"),
    (21, "1-month", "1m"),
    (63, "3-month", "3m"),
)

#: How the comparison instrument is described (proxies named as proxies).
PROXY_LABELS: dict[str, str] = {
    "SPY": "SPY (S&P 500 ETF proxy)",
    "QQQ": "QQQ (Nasdaq-100 ETF proxy)",
}


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:+.{digits}f}%"


def build_relative_section(
    symbol: str,
    bars: list[MarketBarOut],
    context_bars: dict[str, list[MarketBarOut]],
) -> WorkspaceSection:
    """Relative performance vs each context instrument, windowed and cited."""
    statements: list[Statement] = []
    evidence: dict[str, EvidenceItem] = {}
    as_of = bars[-1].bar_date.isoformat() if bars else ""
    asset_by_date = {b.bar_date: float(b.adj_close) for b in bars}

    for context_symbol, cbars in context_bars.items():
        if context_symbol == symbol or not cbars:
            continue
        label = PROXY_LABELS.get(context_symbol, context_symbol)
        bench_by_date = {b.bar_date: float(b.adj_close) for b in cbars}

        parts: list[str] = []
        ids: list[str] = []
        by_window: dict[str, float] = {}
        for window, window_label, suffix in WINDOWS:
            rel = ft.relative_return(asset_by_date, bench_by_date, window)
            if rel is None:
                continue
            eid = f"rel_{suffix}_{context_symbol.lower()}"
            evidence[eid] = EvidenceItem(
                id=eid,
                label=f"{window_label} return vs {context_symbol}",
                value=rel,
                display=_pct(rel),
                as_of=as_of,
                source=f"computed from yahoo:{symbol} and {context_symbol} daily bars",
            )
            ids.append(eid)
            by_window[suffix] = rel
            parts.append(f"{window_label} {_pct(rel)}")

        if not parts:
            continue

        trend = ""
        if "1w" in by_window and "1m" in by_window:
            recent, monthly = by_window["1w"], by_window["1m"]
            if recent > 0 and monthly > 0:
                trend = " Leadership is intact on both horizons."
            elif recent < 0 and monthly > 0:
                trend = (
                    " Monthly leadership, but the last week is lagging — momentum may be cooling."
                )
            elif recent > 0 and monthly < 0:
                trend = " Lagging on the month, but the last week is improving."
            else:
                trend = " Lagging on both horizons."
        statements.append(
            Statement(
                text=(
                    f"Relative to {label}: " + ", ".join(parts) + " (positive = "
                    f"{symbol} outperformed)." + trend
                ),
                evidence_ids=tuple(ids),
            )
        )

    if not statements:
        statements.append(
            Statement(
                text=(
                    "Not enough overlapping history to compute relative performance "
                    "yet — run a refresh once market data is available."
                ),
                evidence_ids=(),
            )
        )

    # Honest gap (ADR-009): no sector/peer comparison until it has a real basis.
    statements.append(
        Statement(
            text=(
                "Sector and peer comparison: not shown — instrument-to-sector "
                "mapping (SEC SIC codes, task C4) has not been built yet. Index "
                "ETF proxies above are the only relative read so far."
            ),
            evidence_ids=(),
        )
    )

    return WorkspaceSection(
        id="relative",
        title="Relative Context",
        statements=statements,
        evidence=list(evidence.values()),
    )
