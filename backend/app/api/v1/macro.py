"""Macro intelligence endpoints: series catalog, bitemporal observations,
and manual ingestion triggers (the scheduler takes over later)."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_nowflation_connector, get_session
from app.connectors.base import ConnectorError
from app.connectors.nowflation import NowflationConnector
from app.repositories.macro import MacroObservationRepository, MacroSeriesRepository
from app.schemas.macro import IngestionReport, MacroObservationOut
from app.services.macro_ingestion import MacroIngestionService

router = APIRouter(prefix="/macro")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class SeriesInfo(BaseModel):
    """API view of a macro series catalog entry."""

    series_id: str
    provider: str
    name: str
    unit: str
    description: str


@router.get("/series")
async def list_series(session: SessionDep) -> list[SeriesInfo]:
    """List all macro series known to the platform."""
    series = await MacroSeriesRepository(session).list_all()
    return [
        SeriesInfo(
            series_id=item.series_id,
            provider=item.provider,
            name=item.name,
            unit=item.unit,
            description=item.description,
        )
        for item in series
    ]


@router.get("/series/{series_id}/observations")
async def get_observations(
    series_id: str,
    session: SessionDep,
    start: Annotated[date | None, Query(description="Earliest observation date")] = None,
    end: Annotated[date | None, Query(description="Latest observation date")] = None,
    as_of: Annotated[
        datetime | None,
        Query(description="Return the series as it was known at this moment (ADR-004)"),
    ] = None,
) -> list[MacroObservationOut]:
    """Bitemporal series query: latest revision per date, as of a moment."""
    observations = await MacroObservationRepository(session).get_observations(
        series_id=series_id, start=start, end=end, as_of=as_of
    )
    if not observations:
        known = {item.series_id for item in await MacroSeriesRepository(session).list_all()}
        if series_id not in known:
            raise HTTPException(status_code=404, detail=f"unknown series: {series_id}")
    return observations


@router.post("/ingest/nowflation", status_code=200)
async def ingest_nowflation(
    session: SessionDep,
    connector: Annotated[NowflationConnector, Depends(get_nowflation_connector)],
) -> IngestionReport:
    """Fetch and store the latest Nowflation headline data (idempotent)."""
    service = MacroIngestionService(session, connector)
    try:
        return await service.ingest_nowflation_headline()
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
