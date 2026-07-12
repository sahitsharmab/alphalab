"""Single-user watchlist endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.watchlist import WatchlistAddRequest, WatchlistItemOut, WatchlistOverviewRow
from app.services.watchlist import WatchlistError, WatchlistService

router = APIRouter(prefix="/watchlist")
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_watchlist(session: SessionDep) -> list[WatchlistItemOut]:
    return await WatchlistService(session).list_items()


@router.post("")
async def add_watchlist_item(request: WatchlistAddRequest, session: SessionDep) -> WatchlistItemOut:
    try:
        return await WatchlistService(session).add(request)
    except WatchlistError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_item(symbol: str, session: SessionDep) -> Response:
    removed = await WatchlistService(session).remove(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} is not on the watchlist")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/overview")
async def watchlist_overview(session: SessionDep) -> list[WatchlistOverviewRow]:
    return await WatchlistService(session).overview()
