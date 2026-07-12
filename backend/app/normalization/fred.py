"""Normalize FRED release-dates payloads into calendar events.

The tracked-release list is deliberate configuration: release ids were
verified against the live FRED catalog on 2026-07-12. Each ``kind`` links
the event to its entry in the catalyst playbook
(``app/config/catalyst_playbook.py``).
"""

import json
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.normalization import NormalizationError
from app.schemas.calendar import CalendarEventIn, CalendarEventType

SOURCE_ID = "fred"


class TrackedRelease(BaseModel):
    """One official economic release whose schedule we ingest."""

    model_config = ConfigDict(frozen=True)

    release_id: int
    kind: str  # playbook key, e.g. "CPI"
    title: str  # displayed event title
    url: str  # public FRED release page (human-readable provenance)


def _release(release_id: int, kind: str, title: str) -> TrackedRelease:
    return TrackedRelease(
        release_id=release_id,
        kind=kind,
        title=title,
        url=f"https://fred.stlouisfed.org/release?rid={release_id}",
    )


#: Verified against /fred/releases on 2026-07-12.
TRACKED_RELEASES: tuple[TrackedRelease, ...] = (
    _release(10, "CPI", "Consumer Price Index (CPI)"),
    _release(46, "PPI", "Producer Price Index (PPI)"),
    _release(50, "EMPLOYMENT", "Employment Situation (jobs report)"),
    _release(9, "RETAIL_SALES", "Advance Retail Sales"),
    _release(53, "GDP", "Gross Domestic Product (GDP)"),
    _release(54, "PCE", "Personal Income and Outlays (PCE inflation)"),
    _release(91, "CONSUMER_SENTIMENT", "University of Michigan Surveys of Consumers"),
)


def parse_release_dates(content: str, release: TrackedRelease) -> list[CalendarEventIn]:
    """Parse one /fred/release/dates response for a tracked release."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"FRED release dates: invalid JSON ({exc})") from exc

    entries = payload.get("release_dates")
    if not isinstance(entries, list):
        raise NormalizationError("FRED release dates: no release_dates array in payload")

    events: list[CalendarEventIn] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise NormalizationError("FRED release dates: malformed entry")
        if entry.get("release_id") != release.release_id:
            raise NormalizationError(
                f"FRED release dates: expected release_id {release.release_id}, "
                f"got {entry.get('release_id')!r}"
            )
        try:
            scheduled_on = date.fromisoformat(str(entry.get("date")))
        except ValueError as exc:
            raise NormalizationError(
                f"FRED release dates: invalid date {entry.get('date')!r}"
            ) from exc
        events.append(
            CalendarEventIn(
                source_id=SOURCE_ID,
                event_type=CalendarEventType.ECONOMIC_RELEASE,
                title=release.title,
                scheduled_on=scheduled_on,
                # FRED publishes dates only, not times-of-day; typical release
                # times are editorial and live in the catalyst playbook.
                scheduled_time="",
                url=release.url,
                provider_metadata={"release_id": release.release_id, "kind": release.kind},
            )
        )
    return events
