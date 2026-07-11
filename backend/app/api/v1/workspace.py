"""Investment Workspace endpoint: ticker → evidence-backed view (ADR-010)."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_yahoo_connector
from app.connectors.base import ConnectorError
from app.connectors.yahoo import YahooConnector
from app.normalization import NormalizationError
from app.schemas.workspace import WorkspaceView
from app.services.market_ingestion import MarketIngestionService
from app.services.workspace import WorkspaceError, WorkspaceService

router = APIRouter(prefix="/workspace")

_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-\^]{1,10}$")


@router.get("/{symbol}")
async def get_workspace(
    symbol: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    connector: Annotated[YahooConnector, Depends(get_yahoo_connector)],
    refresh: Annotated[bool, Query(description="Force re-fetch of market data")] = False,
) -> WorkspaceView:
    """Build (and persist) the Investment Workspace for one symbol."""
    if not _SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=422, detail=f"invalid symbol: {symbol!r}")

    settings = request.app.state.settings
    market = MarketIngestionService(
        session, connector, staleness_days=settings.market_staleness_days
    )
    service = WorkspaceService(session, market, benchmark_symbol=settings.benchmark_symbol)
    try:
        return await service.build(symbol, force_refresh=refresh)
    except ConnectorError as exc:
        # Yahoo answers unknown symbols with HTTP 404.
        if "HTTP 404" in str(exc):
            raise HTTPException(
                status_code=404, detail=f"unknown symbol: {symbol.upper()}"
            ) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (NormalizationError, WorkspaceError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
