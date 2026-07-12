"""Normalizes the Fed calendar JSON into calendar events.

Feed quirks (verified 2026-07-12): UTF-8 BOM prefix; ``month`` is
"YYYY-MM"; ``days`` is a single day or a comma-separated list (recurring
weekly releases list every occurrence — one event row per day). Only
market-relevant event types are normalized (FOMC, Beige Book, statistical
releases); speeches/testimony stay in the raw payload.
"""

import json
from datetime import date

from app.normalization import NormalizationError
from app.schemas.calendar import CalendarEventIn, CalendarEventType

_FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_CALENDAR_URL = "https://www.federalreserve.gov/newsevents/calendar.htm"


def _classify(event_type: str, title: str) -> CalendarEventType | None:
    if event_type == "FOMC":
        lowered = title.lower()
        if "minutes" in lowered:
            return CalendarEventType.FOMC_MINUTES
        if "press conference" in lowered:
            return CalendarEventType.FOMC_PRESS_CONFERENCE
        if "meeting" in lowered:
            return CalendarEventType.FOMC_MEETING
        return None
    if event_type == "Beige":
        return CalendarEventType.BEIGE_BOOK
    if event_type == "Stat":
        return CalendarEventType.FED_STAT_RELEASE
    return None  # speeches, testimony, conferences: not catalysts


def parse_fed_calendar(payload_text: str) -> list[CalendarEventIn]:
    try:
        payload = json.loads(payload_text.lstrip("﻿"))
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"fed calendar: invalid JSON: {exc}") from exc

    raw_events = payload.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise NormalizationError("fed calendar: no events array")

    events: list[CalendarEventIn] = []
    for raw in raw_events:
        classified = _classify(str(raw.get("type") or ""), str(raw.get("title") or ""))
        if classified is None:
            continue
        month = str(raw.get("month") or "")
        days = str(raw.get("days") or "")
        if not month or not days:
            continue
        title = str(raw.get("title") or "").strip()
        url = (
            _FOMC_CALENDAR_URL
            if classified
            in (
                CalendarEventType.FOMC_MEETING,
                CalendarEventType.FOMC_MINUTES,
                CalendarEventType.FOMC_PRESS_CONFERENCE,
            )
            else _CALENDAR_URL
        )
        for day_text in days.split(","):
            day_text = day_text.strip()
            if not day_text.isdigit():
                continue
            try:
                scheduled_on = date.fromisoformat(f"{month}-{int(day_text):02d}")
            except ValueError:
                continue  # tolerate impossible dates rather than fail the feed
            events.append(
                CalendarEventIn(
                    source_id="federal_reserve",
                    event_type=classified,
                    title=title,
                    scheduled_on=scheduled_on,
                    scheduled_time=str(raw.get("time") or "").strip(),
                    url=url,
                    provider_metadata={"fed_type": raw.get("type")},
                )
            )
    if not events:
        raise NormalizationError("fed calendar: no market-relevant events parsed")
    return events
