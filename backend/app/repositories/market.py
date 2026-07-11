"""Repositories for instruments and bitemporal market bars.

Same bitemporal rules as macro (see repositories/macro.py): writes insert
only new/changed bars; reads return the latest revision per bar date with
``as_of`` ≤ the requested moment.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Instrument, MarketBar
from app.schemas.market import InstrumentInfo, MarketBarIn, MarketBarOut

logger = structlog.get_logger(__name__)


class InstrumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, info: InstrumentInfo) -> None:
        statement = (
            pg_insert(Instrument)
            .values(
                symbol=info.symbol,
                name=info.name,
                currency=info.currency,
                exchange=info.exchange,
            )
            .on_conflict_do_update(
                index_elements=[Instrument.symbol],
                set_={"name": info.name, "currency": info.currency, "exchange": info.exchange},
            )
        )
        await self._session.execute(statement)

    async def get(self, symbol: str) -> Instrument | None:
        return await self._session.get(Instrument, symbol)


class MarketBarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_bar_date(self, symbol: str) -> date | None:
        """Newest bar date stored for ``symbol`` (any revision)."""
        result: date | None = await self._session.scalar(
            select(func.max(MarketBar.bar_date)).where(MarketBar.symbol == symbol)
        )
        return result

    async def upsert_bars(
        self,
        bars: list[MarketBarIn],
        as_of: datetime,
        raw_payload_id: int | None,
    ) -> int:
        """Insert bars whose values are new or revised; return count."""
        if not bars:
            return 0
        symbol = bars[0].symbol
        latest = await self._load_latest_closes(symbol)

        inserted = 0
        for bar in bars:
            known = latest.get(bar.bar_date)
            # Adjusted close is the revision-sensitive field (splits and
            # dividends rewrite history); close catches same-day corrections.
            if known is not None and known == (bar.adj_close, bar.close, bar.volume):
                continue
            self._session.add(
                MarketBar(
                    symbol=bar.symbol,
                    bar_date=bar.bar_date,
                    as_of=as_of,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    adj_close=bar.adj_close,
                    volume=bar.volume,
                    raw_payload_id=raw_payload_id,
                )
            )
            inserted += 1
        await self._session.flush()
        logger.info(
            "market_bars_upserted",
            symbol=symbol,
            parsed=len(bars),
            inserted=inserted,
        )
        return inserted

    async def _load_latest_closes(self, symbol: str) -> dict[date, tuple[Decimal, Decimal, int]]:
        """Latest known (adj_close, close, volume) per bar date."""
        latest_as_of = (
            select(
                MarketBar.bar_date,
                func.max(MarketBar.as_of).label("max_as_of"),
            )
            .where(MarketBar.symbol == symbol)
            .group_by(MarketBar.bar_date)
            .subquery()
        )
        rows = await self._session.execute(
            select(
                MarketBar.bar_date,
                MarketBar.adj_close,
                MarketBar.close,
                MarketBar.volume,
            )
            .join(
                latest_as_of,
                (MarketBar.bar_date == latest_as_of.c.bar_date)
                & (MarketBar.as_of == latest_as_of.c.max_as_of),
            )
            .where(MarketBar.symbol == symbol)
        )
        return {row.bar_date: (row.adj_close, row.close, row.volume) for row in rows}

    async def get_bars(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        as_of: datetime | None = None,
    ) -> list[MarketBarOut]:
        """Bars as known at ``as_of`` (default: latest), ascending by date."""
        effective_as_of = as_of or datetime.now(UTC)
        ranked = select(
            MarketBar,
            func.row_number()
            .over(partition_by=MarketBar.bar_date, order_by=MarketBar.as_of.desc())
            .label("revision_rank"),
        ).where(MarketBar.symbol == symbol, MarketBar.as_of <= effective_as_of)
        if start is not None:
            ranked = ranked.where(MarketBar.bar_date >= start)
        if end is not None:
            ranked = ranked.where(MarketBar.bar_date <= end)

        subquery = ranked.subquery()
        bar_alias = subquery.c
        rows = await self._session.execute(
            select(
                bar_alias.symbol,
                bar_alias.bar_date,
                bar_alias.open,
                bar_alias.high,
                bar_alias.low,
                bar_alias.close,
                bar_alias.adj_close,
                bar_alias.volume,
            )
            .where(bar_alias.revision_rank == 1)
            .order_by(bar_alias.bar_date)
        )
        return [
            MarketBarOut(
                symbol=row.symbol,
                bar_date=row.bar_date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                adj_close=row.adj_close,
                volume=row.volume,
            )
            for row in rows
        ]
