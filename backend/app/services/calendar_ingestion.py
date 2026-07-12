"""Calendar ingestion: Fed calendar → raw storage → normalization → events."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.federal_reserve import FederalReserveConnector
from app.normalization.federal_reserve import parse_fed_calendar
from app.repositories.calendar import CalendarEventRepository
from app.repositories.macro import RawPayloadRepository
from app.schemas.calendar import CalendarIngestionReport

logger = structlog.get_logger(__name__)

#: Scheduled calendars change rarely; daily refresh is plenty.
DEFAULT_STALENESS = timedelta(hours=24)


class CalendarIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        connector: FederalReserveConnector,
        staleness: timedelta = DEFAULT_STALENESS,
    ) -> None:
        self._session = session
        self._connector = connector
        self._staleness = staleness
        self._events = CalendarEventRepository(session)
        self._raw_payloads = RawPayloadRepository(session)

    async def ensure_fed_calendar(self, force: bool = False) -> CalendarIngestionReport | None:
        """Ingest the Fed calendar unless already fresh (returns None when fresh)."""
        if not force:
            newest = await self._events.latest_retrieved_at("federal_reserve")
            if newest is not None and newest >= datetime.now(UTC) - self._staleness:
                return None

        fetch = await self._connector.fetch_calendar()
        raw_payload, _reused = await self._raw_payloads.store(
            provider=fetch.provider,
            dataset=fetch.dataset,
            source_url=fetch.url,
            content=fetch.content,
            content_hash=fetch.content_hash,
            retrieved_at=fetch.retrieved_at,
        )
        del raw_payload  # events reference the calendar page URL directly
        events = parse_fed_calendar(fetch.content)
        inserted = await self._events.upsert_events(events, retrieved_at=fetch.retrieved_at)
        logger.info("fed_calendar_ingested", parsed=len(events), inserted=inserted)
        return CalendarIngestionReport(
            source_id="federal_reserve",
            events_parsed=len(events),
            events_inserted=inserted,
            retrieved_at=fetch.retrieved_at,
        )
