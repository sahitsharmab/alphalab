"""Unit tests for Fed calendar normalization and the Catalysts engine."""

import json
from datetime import UTC, date, datetime

import pytest

from app.engines.catalysts import build_catalysts_section
from app.normalization import NormalizationError
from app.normalization.federal_reserve import parse_fed_calendar
from app.schemas.calendar import CalendarEventOut, CalendarEventType

FED_PAYLOAD = "﻿" + json.dumps(
    {
        "events": [
            {
                "title": "FOMC Meeting",
                "type": "FOMC",
                "month": "2026-07",
                "days": "29",
                "time": "2:00 p.m.",
            },
            {
                "title": "FOMC Press Conference",
                "type": "FOMC",
                "month": "2026-07",
                "days": "29",
                "time": "2:30 p.m.",
            },
            {
                "title": "FOMC Minutes",
                "type": "FOMC",
                "month": "2026-08",
                "days": "19",
                "time": "2:00 p.m.",
            },
            {"title": "Beige Book", "type": "Beige", "month": "2026-09", "days": "2", "time": ""},
            {
                "title": "H.4.1 - Factors Affecting Reserve Balances",
                "type": "Stat",
                "month": "2026-07",
                "days": "2, 9, 16",
                "time": "4:30 p.m.",
            },
            {
                "title": "Speech - Someone",
                "type": "Speeches",
                "month": "2026-07",
                "days": "15",
                "time": "9:00 a.m.",
            },
        ]
    }
)


def test_parse_fed_calendar_classifies_and_expands_days() -> None:
    events = parse_fed_calendar(FED_PAYLOAD)

    types = [e.event_type for e in events]
    assert CalendarEventType.FOMC_MEETING in types
    assert CalendarEventType.FOMC_PRESS_CONFERENCE in types
    assert CalendarEventType.FOMC_MINUTES in types
    assert CalendarEventType.BEIGE_BOOK in types
    # comma-list days expand to one event per day
    stat = [e for e in events if e.event_type == CalendarEventType.FED_STAT_RELEASE]
    assert [e.scheduled_on for e in stat] == [
        date(2026, 7, 2),
        date(2026, 7, 9),
        date(2026, 7, 16),
    ]
    # speeches are not catalysts
    assert not any("Speech" in e.title for e in events)
    meeting = next(e for e in events if e.event_type == CalendarEventType.FOMC_MEETING)
    assert meeting.scheduled_on == date(2026, 7, 29)
    assert meeting.url.endswith("fomccalendars.htm")


def test_parse_fed_calendar_rejects_garbage() -> None:
    with pytest.raises(NormalizationError, match="invalid JSON"):
        parse_fed_calendar("<html>blocked</html>")
    with pytest.raises(NormalizationError, match="no events"):
        parse_fed_calendar('{"events": []}')


def _event(
    event_id: int,
    event_type: CalendarEventType,
    title: str,
    scheduled: date,
    time: str = "2:00 p.m.",
) -> CalendarEventOut:
    return CalendarEventOut(
        id=event_id,
        source_id="federal_reserve",
        source_name="Federal Reserve",
        trust_level=10,
        event_type=event_type,
        title=title,
        scheduled_on=scheduled,
        scheduled_time=time,
        url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        retrieved_at=datetime.now(UTC),
    )


def test_catalysts_section_fomc_and_gaps() -> None:
    today = date(2026, 7, 12)
    events = [
        _event(1, CalendarEventType.FOMC_MEETING, "FOMC Meeting", date(2026, 7, 29)),
        _event(
            2, CalendarEventType.FOMC_PRESS_CONFERENCE, "FOMC Press Conference", date(2026, 7, 29)
        ),
        _event(3, CalendarEventType.FOMC_MINUTES, "FOMC Minutes", date(2026, 8, 19)),
        _event(
            4, CalendarEventType.FED_STAT_RELEASE, "G.17 - Industrial Production", date(2026, 7, 17)
        ),
    ]

    section = build_catalysts_section(events, today)

    assert section.id == "catalysts"
    texts = " ".join(s.text for s in section.statements)
    assert "2026-07-29 (in 17 days)" in texts
    assert "press conference the same day" in texts
    assert "FOMC minutes on 2026-08-19" in texts
    assert "Industrial Production" in texts
    # honest gaps: earnings not guessed
    assert "Earnings date: not shown" in texts
    assert all(item.trust_level == 10 for item in section.evidence)


def test_catalysts_section_empty() -> None:
    section = build_catalysts_section([], date(2026, 7, 12))
    assert "No upcoming calendar events" in section.statements[0].text
