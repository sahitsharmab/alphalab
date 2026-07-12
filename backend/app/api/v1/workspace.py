"""Investment Workspace endpoint: ticker → evidence-backed view (ADR-010)."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysts.manual_workspace import build_manual_analysis_packet
from app.api.deps import (
    get_federal_reserve_connector,
    get_sec_edgar_connector,
    get_session,
    get_yahoo_connector,
    get_yahoo_news_connector,
)
from app.connectors.base import ConnectorError
from app.connectors.federal_reserve import FederalReserveConnector
from app.connectors.sec_edgar import SecEdgarConnector
from app.connectors.yahoo import YahooConnector
from app.connectors.yahoo_news import YahooNewsConnector
from app.normalization import NormalizationError
from app.repositories.research import WorkspaceSnapshotRepository
from app.schemas.manual_analysis import ManualAnalysisPacket
from app.schemas.workspace import WorkspaceView
from app.services.calendar_ingestion import CalendarIngestionService
from app.services.evidence_ingestion import EvidenceIngestionService
from app.services.market_ingestion import MarketIngestionService
from app.services.workspace import WorkspaceError, WorkspaceService

router = APIRouter(prefix="/workspace")

_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-\^]{1,10}$")


@router.get("/{symbol}/manual-analysis")
async def get_manual_analysis_packet(
    symbol: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManualAnalysisPacket:
    """Export the latest workspace as a copyable, versioned AI research prompt."""
    if not _SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=422, detail=f"invalid symbol: {symbol!r}")
    view = await WorkspaceSnapshotRepository(session).latest(symbol)
    if view is None:
        raise HTTPException(
            status_code=404,
            detail=f"build the {symbol.upper()} workspace before exporting it",
        )
    return build_manual_analysis_packet(view)


@router.get("/{symbol}")
async def get_workspace(
    symbol: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    connector: Annotated[YahooConnector, Depends(get_yahoo_connector)],
    sec_connector: Annotated[SecEdgarConnector, Depends(get_sec_edgar_connector)],
    news_connector: Annotated[YahooNewsConnector, Depends(get_yahoo_news_connector)],
    fed_connector: Annotated[FederalReserveConnector, Depends(get_federal_reserve_connector)],
    refresh: Annotated[bool, Query(description="Force re-fetch of market data")] = False,
) -> WorkspaceView:
    """Build (and persist) the Investment Workspace for one symbol."""
    if not _SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=422, detail=f"invalid symbol: {symbol!r}")

    settings = request.app.state.settings
    market = MarketIngestionService(
        session, connector, staleness_days=settings.market_staleness_days
    )
    evidence = EvidenceIngestionService(session, sec_connector, news_connector)
    calendar = CalendarIngestionService(session, fed_connector)
    service = WorkspaceService(
        session,
        market,
        evidence=evidence,
        calendar=calendar,
        benchmark_symbol=settings.benchmark_symbol,
    )
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
