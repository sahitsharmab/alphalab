"""Build a deterministic daily momentum overview for user-selected symbols."""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines import decision_board as db
from app.features import technical as ft
from app.repositories.calendar import CalendarEventRepository
from app.repositories.market import InstrumentRepository, MarketBarRepository
from app.repositories.risk import RiskPlanRepository
from app.repositories.watchlist import WatchlistRepository
from app.schemas.calendar import CalendarEventType
from app.schemas.market import MarketBarOut
from app.schemas.watchlist import (
    BoardLevel,
    DecisionBoard,
    DecisionBoardRow,
    WatchlistAddRequest,
    WatchlistItemOut,
    WatchlistOverviewRow,
)

#: Catalyst types worth surfacing as "the next market event" on the board.
_HEADLINE_CATALYSTS = (CalendarEventType.ECONOMIC_RELEASE, CalendarEventType.FOMC_MEETING)


class WatchlistError(Exception):
    """Raised when a symbol has no existing AlphaLab market data."""


class WatchlistService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._items = WatchlistRepository(session)
        self._instruments = InstrumentRepository(session)
        self._bars = MarketBarRepository(session)
        self._calendar = CalendarEventRepository(session)
        self._risk = RiskPlanRepository(session)

    async def add(self, request: WatchlistAddRequest) -> WatchlistItemOut:
        symbol = request.symbol.upper()
        if (
            await self._instruments.get(symbol) is None
            or await self._bars.latest_bar_date(symbol) is None
        ):
            raise WatchlistError(f"build the {symbol} workspace before adding it to the watchlist")
        await self._items.add(symbol, request.note)
        await self._session.commit()
        item = next(item for item in await self._items.list_all() if item.symbol == symbol)
        return WatchlistItemOut(symbol=item.symbol, note=item.note, added_at=item.added_at)

    async def remove(self, symbol: str) -> bool:
        removed = await self._items.remove(symbol)
        await self._session.commit()
        return removed

    async def list_items(self) -> list[WatchlistItemOut]:
        return [
            WatchlistItemOut(symbol=item.symbol, note=item.note, added_at=item.added_at)
            for item in await self._items.list_all()
        ]

    async def board(self) -> DecisionBoard:
        """Compose the Decision Board: role + level bracket + context per name.

        Deterministic (Layer 1): roles are beta bands, levels are the EMAs
        surrounding price, the catalyst is the next shared market event. No
        scenario reasoning is asserted here — that is the reasoning layer.
        """
        today = datetime.now(UTC).date()
        spy_bars = await self._bars.get_bars("SPY")
        spy_by_date = {bar.bar_date: float(bar.adj_close) for bar in spy_bars}

        rows: list[DecisionBoardRow] = []
        for item in await self._items.list_all():
            instrument = await self._instruments.get(item.symbol)
            bars = await self._bars.get_bars(item.symbol)
            if instrument is None or not bars:
                continue
            closes = [float(bar.adj_close) for bar in bars]
            price = float(bars[-1].close)
            asset_by_date = {bar.bar_date: float(bar.adj_close) for bar in bars}
            beta = ft.beta(asset_by_date, spy_by_date) if spy_by_date else None
            support, resistance = db.bracket(price, db.ema_ladder(closes))
            latest_plan = await self._risk.latest(item.symbol)
            rows.append(
                DecisionBoardRow(
                    symbol=item.symbol,
                    name=instrument.name,
                    price=price,
                    price_date=bars[-1].bar_date,
                    role=db.role_for_beta(beta),
                    beta=beta,
                    change_1d=ft.window_return(closes, 1),
                    return_1w=ft.window_return(closes, 5),
                    return_1m=ft.window_return(closes, 21),
                    relative_1m_spy=(
                        ft.relative_return(asset_by_date, spy_by_date, 21) if spy_by_date else None
                    ),
                    support=_level(price, support),
                    resistance=_level(price, resistance),
                    has_risk_plan=latest_plan is not None,
                    note=item.note,
                )
            )

        # Highest-beta first so the board reads as a risk gradient; hedges and
        # unclassified names fall to the bottom.
        rows.sort(key=lambda r: (r.beta is None, -(r.beta if r.beta is not None else 0.0)))
        return DecisionBoard(
            generated_at=datetime.now(UTC),
            next_catalyst=await self._next_catalyst(today),
            rows=rows,
        )

    async def _next_catalyst(self, today: date) -> str | None:
        events = await self._calendar.list_upcoming(today, limit=60)
        if not events:
            return None
        headline = [e for e in events if e.event_type in _HEADLINE_CATALYSTS]
        pick = headline[0] if headline else events[0]
        when = _days_away(today, pick.scheduled_on)
        return f"{pick.title} — {pick.scheduled_on.isoformat()} ({when})"

    async def overview(self) -> list[WatchlistOverviewRow]:
        context = {symbol: await self._bars.get_bars(symbol) for symbol in ("SPY", "QQQ")}
        rows: list[WatchlistOverviewRow] = []
        for item in await self._items.list_all():
            instrument = await self._instruments.get(item.symbol)
            bars = await self._bars.get_bars(item.symbol)
            if instrument is None or not bars:
                continue
            closes = [float(bar.adj_close) for bar in bars]
            price = closes[-1]
            ema9 = ft.ema(closes, 9)
            ema21 = ft.ema(closes, 21)
            by_date = {bar.bar_date: float(bar.adj_close) for bar in bars}
            rows.append(
                WatchlistOverviewRow(
                    symbol=item.symbol,
                    name=instrument.name,
                    price=float(bars[-1].close),
                    price_date=bars[-1].bar_date,
                    change_1d=ft.window_return(closes, 1),
                    return_1w=ft.window_return(closes, 5),
                    return_1m=ft.window_return(closes, 21),
                    ema9_distance=price / ema9 - 1 if ema9 else None,
                    ema21_distance=price / ema21 - 1 if ema21 else None,
                    relative_1m_spy=_relative(by_date, context["SPY"]),
                    relative_1m_qqq=_relative(by_date, context["QQQ"]),
                    note=item.note,
                )
            )
        return rows


def _relative(asset: dict[date, float], benchmark_bars: list[MarketBarOut]) -> float | None:
    benchmark = {bar.bar_date: float(bar.adj_close) for bar in benchmark_bars}
    return ft.relative_return(asset, benchmark, 21)


def _level(price: float, ema: tuple[str, float] | None) -> BoardLevel | None:
    if ema is None or price == 0:
        return None
    label, value = ema
    return BoardLevel(label=label, value=value, distance=value / price - 1)


def _days_away(today: date, target: date) -> str:
    delta = (target - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return f"in {delta} days"
