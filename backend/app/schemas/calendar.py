"""Domain schemas for scheduled events (catalysts)."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class CalendarEventType(StrEnum):
    FOMC_MEETING = "fomc_meeting"
    FOMC_MINUTES = "fomc_minutes"
    FOMC_PRESS_CONFERENCE = "fomc_press_conference"
    BEIGE_BOOK = "beige_book"
    FED_STAT_RELEASE = "fed_stat_release"
    # Scheduled official economic data releases (CPI, PPI, jobs, GDP, ...)
    # via the FRED release-dates API; the release kind lives in
    # provider_metadata["kind"]. Earnings dates: no reliable free source
    # verified yet (source-risk gate, ADR-009).
    ECONOMIC_RELEASE = "economic_release"


class CalendarEventIn(BaseModel):
    """A normalized scheduled event ready for storage."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    event_type: CalendarEventType
    title: str
    scheduled_on: date
    scheduled_time: str = ""  # as published (e.g. "2:00 p.m." ET); "" if none
    url: str = ""
    provider_metadata: dict[str, Any] = {}


class CalendarEventOut(BaseModel):
    id: int
    source_id: str
    source_name: str
    trust_level: int
    event_type: CalendarEventType
    title: str
    scheduled_on: date
    scheduled_time: str
    url: str
    provider_metadata: dict[str, Any] = {}
    retrieved_at: datetime


class CalendarIngestionReport(BaseModel):
    source_id: str
    events_parsed: int
    events_inserted: int
    retrieved_at: datetime
