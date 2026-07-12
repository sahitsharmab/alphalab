"""Evidence endpoints: trust-labeled, entity-linked records (ADR-011/013)."""

import re
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_sec_edgar_connector, get_session
from app.connectors.base import ConnectorError
from app.connectors.sec_edgar import SecEdgarConnector
from app.normalization import NormalizationError
from app.repositories.evidence import EvidenceRepository
from app.schemas.evidence import (
    EntityType,
    EvidenceCategory,
    EvidenceIngestionReport,
    EvidenceRecordOut,
)
from app.services.evidence_ingestion import EvidenceIngestionService, UnknownSymbolError

router = APIRouter(prefix="/evidence")

_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")


class EvidenceResponse(BaseModel):
    """Records plus an optional ingestion report (when a fetch happened)."""

    records: list[EvidenceRecordOut]
    ingestion: EvidenceIngestionReport | None = None


@router.get("/{symbol}")
async def get_evidence(
    symbol: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    connector: Annotated[SecEdgarConnector, Depends(get_sec_edgar_connector)],
    category: Annotated[list[EvidenceCategory] | None, Query()] = None,
    min_trust: Annotated[int | None, Query(ge=0, le=10)] = None,
    since: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    refresh: Annotated[bool, Query(description="Force re-fetch from sources")] = False,
) -> EvidenceResponse:
    """Evidence linked to one instrument, newest first (auto-ingests when stale)."""
    if not _SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=422, detail=f"invalid symbol: {symbol!r}")
    symbol = symbol.upper()

    service = EvidenceIngestionService(session, connector)
    try:
        ingestion = await service.ensure_sec_filings(symbol, force=refresh)
        await session.commit()
    except UnknownSymbolError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ConnectorError, NormalizationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    records = await EvidenceRepository(session).list_for_entity(
        EntityType.INSTRUMENT,
        symbol,
        categories=category,
        min_trust=min_trust,
        since=since,
        limit=limit,
    )
    return EvidenceResponse(records=records, ingestion=ingestion)
