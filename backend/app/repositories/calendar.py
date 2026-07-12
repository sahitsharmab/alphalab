"""Repository for calendar events (catalysts)."""

from datetime import date, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.evidence_sources import require_source
from app.models.calendar import CalendarEvent
from app.schemas.calendar import CalendarEventIn, CalendarEventOut, CalendarEventType

logger = structlog.get_logger(__name__)


class CalendarEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_events(self, events: list[CalendarEventIn], retrieved_at: datetime) -> int:
        """Insert events not stored yet (by source/type/date/title)."""
        if not events:
            return 0
        source_ids = {event.source_id for event in events}
        rows = await self._session.execute(
            select(
                CalendarEvent.source_id,
                CalendarEvent.event_type,
                CalendarEvent.scheduled_on,
                CalendarEvent.title,
            ).where(CalendarEvent.source_id.in_(source_ids))
        )
        existing = {(r.source_id, r.event_type, r.scheduled_on, r.title) for r in rows}

        inserted = 0
        for event in events:
            key = (event.source_id, event.event_type.value, event.scheduled_on, event.title)
            if key in existing:
                continue
            existing.add(key)
            source = require_source(event.source_id)
            self._session.add(
                CalendarEvent(
                    source_id=event.source_id,
                    trust_level=source.trust_level,
                    event_type=event.event_type,
                    title=event.title,
                    scheduled_on=event.scheduled_on,
                    scheduled_time=event.scheduled_time,
                    url=event.url,
                    provider_metadata=dict(event.provider_metadata),
                    retrieved_at=retrieved_at,
                )
            )
            inserted += 1
        await self._session.flush()
        logger.info("calendar_events_upserted", parsed=len(events), inserted=inserted)
        return inserted

    async def list_upcoming(self, on_or_after: date, limit: int = 50) -> list[CalendarEventOut]:
        rows = await self._session.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.scheduled_on >= on_or_after)
            .order_by(CalendarEvent.scheduled_on, CalendarEvent.id)
            .limit(limit)
        )
        return [
            CalendarEventOut(
                id=row.id,
                source_id=row.source_id,
                source_name=require_source(row.source_id).name,
                trust_level=row.trust_level,
                event_type=CalendarEventType(row.event_type),
                title=row.title,
                scheduled_on=row.scheduled_on,
                scheduled_time=row.scheduled_time,
                url=row.url,
                retrieved_at=row.retrieved_at,
            )
            for row in rows
        ]

    async def latest_retrieved_at(self, source_id: str) -> datetime | None:
        result: datetime | None = await self._session.scalar(
            select(func.max(CalendarEvent.retrieved_at)).where(CalendarEvent.source_id == source_id)
        )
        return result
