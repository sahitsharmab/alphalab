"""Evidence Engine: turns stored evidence records into a workspace section.

Deterministic summarization only — counts, recency, categories. Every
statement cites the underlying records; trust levels ride along so the
reader (and any future Decision Framework) can weigh sources themselves.
"""

from datetime import UTC, datetime, timedelta

from app.schemas.evidence import EvidenceCategory, EvidenceRecordOut
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

#: Recency window for the filings summary statement.
RECENT_WINDOW_DAYS = 90


def _to_item(record: EvidenceRecordOut) -> EvidenceItem:
    return EvidenceItem(
        id=f"ev{record.id}",
        label=record.title,
        value=None,
        display=record.category.replace("_", " "),
        as_of=record.published_at.date().isoformat(),
        source=record.source_name,
        trust_level=record.trust_level,
        url=record.url,
    )


def build_company_evidence_section(records: list[EvidenceRecordOut]) -> WorkspaceSection:
    """Company Evidence: filings first (high trust), coverage second."""
    statements: list[Statement] = []
    evidence: dict[str, EvidenceItem] = {}

    def cite(items: list[EvidenceRecordOut]) -> tuple[str, ...]:
        ids = []
        for record in items:
            item = _to_item(record)
            evidence[item.id] = item
            ids.append(item.id)
        return tuple(ids)

    filings = [r for r in records if r.source_id == "sec_edgar"]
    coverage = [r for r in records if r.source_type == "media"]

    if not records:
        statements.append(
            Statement(
                text=(
                    "No evidence records available yet for this symbol — "
                    "sources may still be ingesting, or it may not be a US filer."
                ),
                evidence_ids=(),
            )
        )
        return WorkspaceSection(
            id="evidence", title="Company Evidence", statements=statements, evidence=[]
        )

    if filings:
        cutoff = datetime.now(UTC) - timedelta(days=RECENT_WINDOW_DAYS)
        recent = [f for f in filings if f.published_at >= cutoff]
        earnings = [f for f in filings if f.category == EvidenceCategory.EARNINGS]
        cited = cite(filings[:5])
        summary = (
            f"{len(recent)} SEC filing{'s' if len(recent) != 1 else ''} in the last "
            f"{RECENT_WINDOW_DAYS} days"
            if recent
            else f"No SEC filings in the last {RECENT_WINDOW_DAYS} days"
        )
        latest = filings[0]
        statements.append(
            Statement(
                text=(
                    f"{summary}; most recent: {latest.title} "
                    f"({latest.published_at.date().isoformat()}). Filings are primary "
                    "sources — read them before any commentary."
                ),
                evidence_ids=cited,
            )
        )
        if earnings:
            latest_earnings = earnings[0]
            statements.append(
                Statement(
                    text=(
                        f"Latest earnings-related filing: {latest_earnings.title} on "
                        f"{latest_earnings.published_at.date().isoformat()} — the "
                        "primary record of reported results."
                    ),
                    evidence_ids=cite([latest_earnings]),
                )
            )

    if coverage:
        cited = cite(coverage[:5])
        statements.append(
            Statement(
                text=(
                    f"Recent coverage mentioning the ticker ({len(coverage)} items). "
                    "This is aggregated commentary (trust "
                    f"{coverage[0].trust_level}/10), not primary evidence — useful "
                    "for context and sentiment, never as a basis on its own."
                ),
                evidence_ids=cited,
            )
        )

    return WorkspaceSection(
        id="evidence",
        title="Company Evidence",
        statements=statements,
        evidence=list(evidence.values()),
    )
