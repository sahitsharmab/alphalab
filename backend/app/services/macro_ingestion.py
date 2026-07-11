"""Orchestrates one macro ingestion run: fetch → raw storage → normalize →
bitemporal storage.

The layers stay ignorant of each other; this service is the only place
that sequences them (ARCHITECTURE.md dependency rules).
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.nowflation import NowflationConnector
from app.normalization.nowflation import NOWFLATION_SERIES, normalize_headline_csv
from app.repositories.macro import (
    MacroObservationRepository,
    MacroSeriesRepository,
    RawPayloadRepository,
)
from app.schemas.macro import IngestionReport

logger = structlog.get_logger(__name__)


class MacroIngestionService:
    """Runs macro data ingestion end to end inside a single transaction."""

    def __init__(self, session: AsyncSession, connector: NowflationConnector) -> None:
        self._session = session
        self._connector = connector
        self._raw_payloads = RawPayloadRepository(session)
        self._series = MacroSeriesRepository(session)
        self._observations = MacroObservationRepository(session)

    async def ingest_nowflation_headline(self) -> IngestionReport:
        """Ingest the Nowflation headline gauge (idempotent)."""
        fetch = await self._connector.fetch_headline()

        await self._series.upsert(NOWFLATION_SERIES)
        raw_payload, reused = await self._raw_payloads.store(
            provider=fetch.provider,
            dataset=fetch.dataset,
            source_url=fetch.url,
            content=fetch.content,
            content_hash=fetch.content_hash,
            retrieved_at=fetch.retrieved_at,
        )

        observations = normalize_headline_csv(fetch.content)
        # ``as_of`` is the retrieval time: Nowflation exposes no publication
        # vintages, so knowledge time starts when we saw the data (ADR-004).
        inserted = await self._observations.upsert_observations(
            observations,
            as_of=fetch.retrieved_at,
            raw_payload_id=raw_payload.id,
        )
        await self._session.commit()

        report = IngestionReport(
            provider=fetch.provider,
            dataset=fetch.dataset,
            raw_payload_id=raw_payload.id,
            raw_payload_reused=reused,
            observations_parsed=len(observations),
            observations_inserted=inserted,
            retrieved_at=fetch.retrieved_at,
        )
        logger.info("macro_ingestion_completed", **report.model_dump(mode="json"))
        return report
