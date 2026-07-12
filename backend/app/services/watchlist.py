"""Build a deterministic daily momentum overview for user-selected symbols."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.features import technical as ft
from app.repositories.market import InstrumentRepository, MarketBarRepository
from app.repositories.watchlist import WatchlistRepository
from app.schemas.market import MarketBarOut
from app.schemas.watchlist import WatchlistAddRequest, WatchlistItemOut, WatchlistOverviewRow


class WatchlistError(Exception):
    """Raised when a symbol has no existing AlphaLab market data."""


class WatchlistService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._items = WatchlistRepository(session)
        self._instruments = InstrumentRepository(session)
        self._bars = MarketBarRepository(session)

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
