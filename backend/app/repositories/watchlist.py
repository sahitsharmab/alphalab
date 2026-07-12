"""Watchlist persistence."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlist import WatchlistItem


class WatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, symbol: str, note: str) -> None:
        statement = (
            pg_insert(WatchlistItem)
            .values(symbol=symbol.upper(), note=note)
            .on_conflict_do_update(index_elements=[WatchlistItem.symbol], set_={"note": note})
        )
        await self._session.execute(statement)

    async def remove(self, symbol: str) -> bool:
        normalized = symbol.upper()
        exists = await self._session.scalar(
            select(WatchlistItem.symbol).where(WatchlistItem.symbol == normalized)
        )
        if exists is None:
            return False
        await self._session.execute(delete(WatchlistItem).where(WatchlistItem.symbol == normalized))
        return True

    async def list_all(self) -> list[WatchlistItem]:
        rows = await self._session.scalars(
            select(WatchlistItem).order_by(WatchlistItem.added_at, WatchlistItem.symbol)
        )
        return list(rows)
