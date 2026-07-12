"""Technical Engine: deterministic trend/momentum/volatility statements.

Consumes normalized bars, computes features (ADR-008 pure functions), and
emits workspace sections whose every claim carries evidence (ADR-010).
"""

from app.features import technical as ft
from app.schemas.market import MarketBarOut
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

# Classification thresholds (documented, not magic: referenced in statements)
RSI_OVERBOUGHT = 70.0
RSI_OVERSOLD = 30.0
ELEVATED_RELATIVE_VOLUME = 1.5


class _SectionBuilder:
    """Accumulates statements + evidence with id integrity."""

    def __init__(self, section_id: str, title: str, source: str, as_of: str) -> None:
        self.section_id = section_id
        self.title = title
        self._source = source
        self._as_of = as_of
        self._statements: list[Statement] = []
        self._evidence: dict[str, EvidenceItem] = {}

    def evidence(self, eid: str, label: str, value: float | None, display: str) -> str:
        self._evidence[eid] = EvidenceItem(
            id=eid,
            label=label,
            value=value,
            display=display,
            as_of=self._as_of,
            source=self._source,
        )
        return eid

    def say(self, text: str, *evidence_ids: str) -> None:
        self._statements.append(Statement(text=text, evidence_ids=tuple(evidence_ids)))

    def build(self) -> WorkspaceSection:
        return WorkspaceSection(
            id=self.section_id,
            title=self.title,
            statements=self._statements,
            evidence=list(self._evidence.values()),
        )


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def build_technical_section(symbol: str, bars: list[MarketBarOut]) -> WorkspaceSection:
    """Trend, momentum, volatility, and volume — with the numbers."""
    closes = [float(b.adj_close) for b in bars]
    highs = [float(b.high) for b in bars]
    lows = [float(b.low) for b in bars]
    volumes = [float(b.volume) for b in bars]
    as_of = bars[-1].bar_date.isoformat() if bars else ""
    section = _SectionBuilder(
        "technical", "Technical Overview", f"yahoo:{symbol} daily bars", as_of
    )
    if len(bars) < 30:
        section.say(
            f"Not enough price history for a technical read ({len(bars)} bars available; "
            "at least 30 required). Interpret this workspace with caution."
        )
        return section.build()

    price = closes[-1]
    price_id = section.evidence("last_close", "Last close (adjusted)", price, f"{price:,.2f}")

    # --- Trend: price vs EMA50 / EMA200 ---
    ema50 = ft.ema(closes, 50)
    ema200 = ft.ema(closes, 200)
    if ema50 is not None and ema200 is not None:
        e50 = section.evidence("ema50", "50-day EMA", ema50, f"{ema50:,.2f}")
        e200 = section.evidence("ema200", "200-day EMA", ema200, f"{ema200:,.2f}")
        above50, above200 = price > ema50, price > ema200
        if above50 and above200:
            trend = "In an uptrend"
        elif not above50 and not above200:
            trend = "In a downtrend"
        else:
            trend = "Trend is mixed"
        section.say(
            f"{trend}: price is {_pct(abs(price / ema50 - 1))} "
            f"{'above' if above50 else 'below'} the 50-day EMA and "
            f"{_pct(abs(price / ema200 - 1))} {'above' if above200 else 'below'} "
            f"the 200-day EMA.",
            price_id,
            e50,
            e200,
        )
    elif ema50 is not None:
        e50 = section.evidence("ema50", "50-day EMA", ema50, f"{ema50:,.2f}")
        section.say(
            f"Price is {_pct(abs(price / ema50 - 1))} "
            f"{'above' if price > ema50 else 'below'} the 50-day EMA "
            "(history too short for the 200-day view).",
            price_id,
            e50,
        )

    # --- Short-term structure: price vs EMA9/EMA21 (1-5 day horizon) ---
    ema9 = ft.ema(closes, 9)
    ema21 = ft.ema(closes, 21)
    if ema9 is not None and ema21 is not None:
        e9 = section.evidence("ema9", "9-day EMA", ema9, f"{ema9:,.2f}")
        e21 = section.evidence("ema21", "21-day EMA", ema21, f"{ema21:,.2f}")
        above9, above21 = price > ema9, price > ema21
        if above9 and above21:
            structure = "constructive (price above both)"
        elif not above9 and not above21:
            structure = "weak (price below both)"
        else:
            structure = "mixed"
        section.say(
            f"Short-term structure is {structure}: price is "
            f"{_pct(abs(price / ema9 - 1))} {'above' if above9 else 'below'} the 9-day EMA "
            f"and {_pct(abs(price / ema21 - 1))} {'above' if above21 else 'below'} the "
            "21-day EMA — the 1-5 day momentum read.",
            price_id,
            e9,
            e21,
        )

    # --- Momentum: RSI + short-window returns ---
    rsi14 = ft.rsi(closes, 14)
    r1m = ft.window_return(closes, 21)
    r3m = ft.window_return(closes, 63)
    if rsi14 is not None:
        rsi_id = section.evidence("rsi14", "RSI (14-day)", rsi14, f"{rsi14:.1f}")
        zone = (
            f"overbought territory (>{RSI_OVERBOUGHT:.0f})"
            if rsi14 >= RSI_OVERBOUGHT
            else f"oversold territory (<{RSI_OVERSOLD:.0f})"
            if rsi14 <= RSI_OVERSOLD
            else "neutral territory"
        )
        parts = [f"RSI(14) at {rsi14:.1f} is in {zone}"]
        ids = [rsi_id]
        if r1m is not None:
            ids.append(section.evidence("ret_1m", "1-month return", r1m, _pct(r1m)))
            parts.append(f"1-month return {_pct(r1m)}")
        if r3m is not None:
            ids.append(section.evidence("ret_3m", "3-month return", r3m, _pct(r3m)))
            parts.append(f"3-month return {_pct(r3m)}")
        section.say("Momentum: " + "; ".join(parts) + ".", *ids)

    # --- Volatility: realized vol + ATR ---
    vol20 = ft.realized_volatility(closes, 20)
    vol252 = ft.realized_volatility(closes, min(252, len(closes) - 1))
    atr = ft.atr_fraction(highs, lows, closes, 14)
    if vol20 is not None:
        ids = [
            section.evidence("vol20", "Realized volatility (20d, annualized)", vol20, _pct(vol20))
        ]
        text = f"Realized volatility is {_pct(vol20)} annualized over the past 20 days"
        if vol252 is not None:
            ids.append(
                section.evidence(
                    "vol1y", "Realized volatility (1y, annualized)", vol252, _pct(vol252)
                )
            )
            comparison = (
                "elevated versus"
                if vol20 > vol252 * 1.25
                else "subdued versus"
                if vol20 < vol252 * 0.8
                else "in line with"
            )
            text += f", {comparison} its one-year average of {_pct(vol252)}"
        if atr is not None:
            ids.append(section.evidence("atr14", "ATR (14d, % of price)", atr, _pct(atr)))
            text += f"; average daily true range is {_pct(atr)} of price"
        section.say(text + ".", *ids)

    # --- Volume ---
    rel_vol = ft.relative_volume(volumes, 20)
    if rel_vol is not None:
        rv = section.evidence(
            "rel_volume", "Relative volume (vs 20d average)", rel_vol, f"{rel_vol:.2f}x"
        )
        if rel_vol >= ELEVATED_RELATIVE_VOLUME:
            section.say(
                f"Volume is elevated: last session traded {rel_vol:.2f}x its 20-day "
                "average — something has the market's attention.",
                rv,
            )
        else:
            section.say(
                f"Volume is unremarkable: last session traded {rel_vol:.2f}x its 20-day average.",
                rv,
            )

    return section.build()


def build_historical_section(
    symbol: str,
    bars: list[MarketBarOut],
    benchmark_symbol: str | None = None,
    benchmark_bars: list[MarketBarOut] | None = None,
) -> WorkspaceSection:
    """Returns, drawdown, range position, beta — the base-rate context."""
    closes = [float(b.adj_close) for b in bars]
    as_of = bars[-1].bar_date.isoformat() if bars else ""
    section = _SectionBuilder(
        "historical", "Historical Context", f"yahoo:{symbol} daily bars", as_of
    )
    if len(bars) < 30:
        section.say("Not enough history for historical context.")
        return section.build()

    windows = (("6-month", 126, "ret_6m"), ("1-year", 252, "ret_1y"), ("3-year", 756, "ret_3y"))
    ids = []
    parts = []
    for label, days, eid in windows:
        r = ft.window_return(closes, days)
        if r is not None:
            ids.append(section.evidence(eid, f"{label} return", r, _pct(r)))
            parts.append(f"{label} {_pct(r)}")
    if parts:
        section.say("Trailing returns: " + ", ".join(parts) + ".", *ids)

    drawdown = ft.max_drawdown(closes, 252)
    if drawdown is not None:
        dd = section.evidence("mdd_1y", "Max drawdown (1y)", drawdown, _pct(drawdown))
        section.say(
            f"The worst peak-to-trough decline over the past year was {_pct(drawdown)} — "
            "size any position so that a repeat is survivable.",
            dd,
        )

    position = ft.range_position(closes, 252)
    if position is not None:
        rp = section.evidence(
            "range_pos", "Position in 52-week range", position, f"{position * 100:.0f}%"
        )
        location = (
            "near the high" if position > 0.8 else "near the low" if position < 0.2 else "mid-range"
        )
        section.say(
            f"Price sits at {position * 100:.0f}% of its 52-week range ({location}).",
            rp,
        )

    if benchmark_symbol and benchmark_bars:
        asset_by_date = {b.bar_date: float(b.adj_close) for b in bars}
        bench_by_date = {b.bar_date: float(b.adj_close) for b in benchmark_bars}
        b = ft.beta(asset_by_date, bench_by_date, 252)
        if b is not None:
            beta_id = section.evidence("beta_1y", f"Beta vs {benchmark_symbol} (1y)", b, f"{b:.2f}")
            sensitivity = "amplifies" if b > 1.2 else "dampens" if b < 0.8 else "roughly tracks"
            section.say(
                f"Beta of {b:.2f} vs {benchmark_symbol}: the stock {sensitivity} "
                "broad-market moves — factor this into portfolio-level risk.",
                beta_id,
            )

    return section.build()
