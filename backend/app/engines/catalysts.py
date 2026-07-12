"""Catalysts Engine: upcoming scheduled events as a workspace section.

Deterministic: dates, day counts, and honest gaps (earnings dates have no
reliable free source yet — the section says so instead of guessing).
"""

from datetime import date

from app.schemas.calendar import CalendarEventOut, CalendarEventType
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

#: How many upcoming Fed statistical releases to surface.
MAX_STAT_RELEASES = 3


def _days_away(today: date, target: date) -> str:
    delta = (target - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return f"in {delta} days"


def _to_item(event: CalendarEventOut) -> EvidenceItem:
    time_note = f" {event.scheduled_time} ET" if event.scheduled_time else ""
    return EvidenceItem(
        id=f"cal{event.id}",
        label=event.title,
        value=None,
        display=f"{event.scheduled_on.isoformat()}{time_note}",
        as_of=event.scheduled_on.isoformat(),
        source=event.source_name,
        trust_level=event.trust_level,
        url=event.url or None,
    )


def build_catalysts_section(events: list[CalendarEventOut], today: date) -> WorkspaceSection:
    """Upcoming Catalysts: FOMC, Beige Book, notable Fed releases."""
    statements: list[Statement] = []
    evidence: dict[str, EvidenceItem] = {}

    def cite(items: list[CalendarEventOut]) -> tuple[str, ...]:
        ids = []
        for event in items:
            item = _to_item(event)
            evidence[item.id] = item
            ids.append(item.id)
        return tuple(ids)

    def next_of(*types: CalendarEventType) -> CalendarEventOut | None:
        for event in events:  # events arrive ordered by date
            if event.event_type in types:
                return event
        return None

    fomc = next_of(CalendarEventType.FOMC_MEETING)
    if fomc is not None:
        same_day_press = [
            e
            for e in events
            if e.event_type == CalendarEventType.FOMC_PRESS_CONFERENCE
            and e.scheduled_on == fomc.scheduled_on
        ]
        statements.append(
            Statement(
                text=(
                    f"Next FOMC rate decision: {fomc.scheduled_on.isoformat()} "
                    f"({_days_away(today, fomc.scheduled_on)})"
                    f"{', with a press conference the same day' if same_day_press else ''}. "
                    "Policy decisions move rates, multiples, and high-beta names most."
                ),
                evidence_ids=cite([fomc, *same_day_press]),
            )
        )

    minutes = next_of(CalendarEventType.FOMC_MINUTES)
    beige = next_of(CalendarEventType.BEIGE_BOOK)
    secondary = [e for e in (minutes, beige) if e is not None]
    if secondary:
        parts = [
            f"{'FOMC minutes' if e.event_type == CalendarEventType.FOMC_MINUTES else 'Beige Book'} "
            f"on {e.scheduled_on.isoformat()} ({_days_away(today, e.scheduled_on)})"
            for e in secondary
        ]
        statements.append(
            Statement(
                text=(
                    "Also on the Fed calendar: " + "; ".join(parts) + " — secondary "
                    "events, but both can shift rate expectations."
                ),
                evidence_ids=cite(secondary),
            )
        )

    stats = [e for e in events if e.event_type == CalendarEventType.FED_STAT_RELEASE][
        :MAX_STAT_RELEASES
    ]
    if stats:
        parts = [f"{e.title.strip()} ({e.scheduled_on.isoformat()})" for e in stats]
        statements.append(
            Statement(
                text="Upcoming Federal Reserve data releases: " + "; ".join(parts) + ".",
                evidence_ids=cite(stats),
            )
        )

    # Honest gap, per the source-risk gate (ADR-009/011): no guessing.
    statements.append(
        Statement(
            text=(
                "Earnings date: not shown — no reliable free source has been verified "
                "yet (watch the company's own 8-K/press release announcing the call). "
                "CPI/jobs/GDP release dates arrive with the FRED connector."
            ),
            evidence_ids=(),
        )
    )

    if not evidence:
        statements.insert(
            0,
            Statement(
                text="No upcoming calendar events ingested yet — run a refresh.",
                evidence_ids=(),
            ),
        )

    return WorkspaceSection(
        id="catalysts",
        title="Upcoming Catalysts",
        statements=statements,
        evidence=list(evidence.values()),
    )
