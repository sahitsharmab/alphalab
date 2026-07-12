"""Catalysts Engine: a chronological timeline of upcoming scheduled events.

Deterministic. Each event statement carries the event's evidence (date,
source, trust) plus an editorial ``assessment`` from the versioned catalyst
playbook (ADR-016) — why it matters, transmission chain, what to watch,
conditional scenarios. Honest gaps stay honest: earnings dates have no
verified free source, and per-event historical sensitivity is reported as
not yet measured until a real event study exists.
"""

from datetime import date, timedelta

from app.config.catalyst_playbook import PLAYBOOK_VERSION, get_assessment
from app.schemas.calendar import CalendarEventOut, CalendarEventType
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

#: Economic releases beyond this window are noise for a 1-5 day decision.
HORIZON_DAYS = 14

#: How many upcoming Fed statistical releases to surface.
MAX_STAT_RELEASES = 3

#: Maps Fed-calendar event types to their playbook kind.
_FED_EVENT_KINDS = {
    CalendarEventType.FOMC_MEETING: "FOMC_MEETING",
    CalendarEventType.FOMC_MINUTES: "FOMC_MINUTES",
    CalendarEventType.BEIGE_BOOK: "BEIGE_BOOK",
}


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


def build_catalysts_section(
    events: list[CalendarEventOut],
    today: date,
    symbol: str = "",
    beta_1y: float | None = None,
    beta_benchmark: str = "SPY",
    beta_as_of: str = "",
) -> WorkspaceSection:
    """Catalyst timeline: economic releases, FOMC events, honest gaps."""
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

    # --- Framing: how to read this timeline (editorial vs measured) ---
    framing_ids: tuple[str, ...] = ()
    framing = (
        f"How to read this timeline: importance ratings and scenarios come from "
        f"the AlphaLab playbook v{PLAYBOOK_VERSION} — editorial configuration, "
        f"not measured evidence. Historical per-event sensitivity"
        f"{f' for {symbol}' if symbol else ''}: not yet measured."
    )
    if beta_1y is not None:
        sensitivity = (
            "amplified" if beta_1y > 1.2 else "dampened" if beta_1y < 0.8 else "roughly tracked"
        )
        framing += (
            f" As a starting point, 1-year beta vs {beta_benchmark} is {beta_1y:.2f}: "
            f"market-level reactions to these events have historically been "
            f"{sensitivity} in this stock."
        )
        beta_item = EvidenceItem(
            id="beta_1y",
            label=f"Beta vs {beta_benchmark} (1y)",
            value=beta_1y,
            display=f"{beta_1y:.2f}",
            as_of=beta_as_of,
            source=f"computed from yahoo:{symbol} and {beta_benchmark} daily bars",
        )
        evidence[beta_item.id] = beta_item
        framing_ids = (beta_item.id,)
    statements.append(Statement(text=framing, evidence_ids=framing_ids))

    # --- Timeline entries, assembled then sorted chronologically ---
    timeline: list[tuple[date, Statement]] = []

    horizon_end = today + timedelta(days=HORIZON_DAYS)

    for event in events:
        if event.event_type is not CalendarEventType.ECONOMIC_RELEASE:
            continue
        if event.scheduled_on > horizon_end:
            continue
        kind = str(event.provider_metadata.get("kind", ""))
        assessment = get_assessment(kind)
        text = (
            f"{event.title}: {event.scheduled_on.isoformat()} "
            f"({_days_away(today, event.scheduled_on)})."
        )
        if assessment is not None:
            text += f" Playbook importance: {assessment.importance}."
        timeline.append(
            (
                event.scheduled_on,
                Statement(text=text, evidence_ids=cite([event]), assessment=assessment),
            )
        )

    fomc = next_of(CalendarEventType.FOMC_MEETING)
    if fomc is not None:
        same_day_press = [
            e
            for e in events
            if e.event_type == CalendarEventType.FOMC_PRESS_CONFERENCE
            and e.scheduled_on == fomc.scheduled_on
        ]
        timeline.append(
            (
                fomc.scheduled_on,
                Statement(
                    text=(
                        f"Next FOMC rate decision: {fomc.scheduled_on.isoformat()} "
                        f"({_days_away(today, fomc.scheduled_on)})"
                        f"{', with a press conference the same day' if same_day_press else ''}. "
                        "Policy decisions move rates, multiples, and high-beta names most."
                    ),
                    evidence_ids=cite([fomc, *same_day_press]),
                    assessment=get_assessment("FOMC_MEETING"),
                ),
            )
        )

    for event_type, label in (
        (CalendarEventType.FOMC_MINUTES, "FOMC minutes"),
        (CalendarEventType.BEIGE_BOOK, "Beige Book"),
    ):
        secondary = next_of(event_type)
        if secondary is not None:
            timeline.append(
                (
                    secondary.scheduled_on,
                    Statement(
                        text=(
                            f"{label} on {secondary.scheduled_on.isoformat()} "
                            f"({_days_away(today, secondary.scheduled_on)}) — a secondary "
                            "event, but it can shift rate expectations."
                        ),
                        evidence_ids=cite([secondary]),
                        assessment=get_assessment(_FED_EVENT_KINDS[event_type]),
                    ),
                )
            )

    stats = [e for e in events if e.event_type == CalendarEventType.FED_STAT_RELEASE][
        :MAX_STAT_RELEASES
    ]
    if stats:
        parts = [f"{e.title.strip()} ({e.scheduled_on.isoformat()})" for e in stats]
        timeline.append(
            (
                stats[0].scheduled_on,
                Statement(
                    text="Upcoming Federal Reserve data releases: " + "; ".join(parts) + ".",
                    evidence_ids=cite(stats),
                ),
            )
        )

    timeline.sort(key=lambda entry: entry[0])
    statements.extend(statement for _, statement in timeline)

    # --- Honest gaps, per the source-risk gate (ADR-009/011): no guessing ---
    gaps = (
        "Earnings date: not shown — no reliable free source has been verified "
        "yet (watch the company's own 8-K/press release announcing the call)."
    )
    if not any(e.event_type is CalendarEventType.ECONOMIC_RELEASE for e in events):
        gaps += (
            " Economic release dates (CPI, PPI, jobs report, GDP) are not "
            "available — the FRED connector has not ingested yet (it needs a "
            "free API key, ALPHALAB_FRED_API_KEY)."
        )
    statements.append(Statement(text=gaps, evidence_ids=()))

    if not events:
        statements.insert(
            0,
            Statement(
                text="No upcoming calendar events ingested yet — run a refresh.",
                evidence_ids=(),
            ),
        )

    return WorkspaceSection(
        id="catalysts",
        title="Catalyst Timeline",
        statements=statements,
        evidence=list(evidence.values()),
    )
