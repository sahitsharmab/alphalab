"""Calendar ingestion: scheduled-event sources → raw storage → events.

Sources: the Fed's own calendar (FOMC, Beige Book, stat releases) and the
FRED release-dates API (CPI, PPI, jobs, GDP, ... — optional, needs a key).
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.federal_reserve import FederalReserveConnector
from app.connectors.fred import FredConnector
from app.normalization.federal_reserve import parse_fed_calendar
from app.normalization.fred import TRACKED_RELEASES, parse_release_dates
from app.repositories.calendar import CalendarEventRepository
from app.repositories.macro import RawPayloadRepository
from app.schemas.calendar import CalendarEventIn, CalendarIngestionReport

logger = structlog.get_logger(__name__)

#: Scheduled calendars change rarely; daily refresh is plenty.
DEFAULT_STALENESS = timedelta(hours=24)


class CalendarIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        connector: FederalReserveConnector,
        fred: FredConnector | None = None,
        staleness: timedelta = DEFAULT_STALENESS,
    ) -> None:
        self._session = session
        self._connector = connector
        self._fred = fred
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

    async def ensure_economic_releases(self, force: bool = False) -> CalendarIngestionReport | None:
        """Ingest FRED release dates unless fresh or unconfigured (None either way)."""
        if self._fred is None:
            return None
        if not force:
            newest = await self._events.latest_retrieved_at("fred")
            if newest is not None and newest >= datetime.now(UTC) - self._staleness:
                return None

        today = datetime.now(UTC).date()
        events: list[CalendarEventIn] = []
        retrieved_at = datetime.now(UTC)
        for release in TRACKED_RELEASES:
            fetch = await self._fred.fetch_release_dates(release.release_id, today)
            await self._raw_payloads.store(
                provider=fetch.provider,
                dataset=f"{fetch.dataset}.{release.kind.lower()}",
                source_url=fetch.url,
                content=fetch.content,
                content_hash=fetch.content_hash,
                retrieved_at=fetch.retrieved_at,
            )
            events.extend(parse_release_dates(fetch.content, release))
            retrieved_at = fetch.retrieved_at
        inserted = await self._events.upsert_events(events, retrieved_at=retrieved_at)
        logger.info("fred_release_dates_ingested", parsed=len(events), inserted=inserted)
        return CalendarIngestionReport(
            source_id="fred",
            events_parsed=len(events),
            events_inserted=inserted,
            retrieved_at=retrieved_at,
        )
