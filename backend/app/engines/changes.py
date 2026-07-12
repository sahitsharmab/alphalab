"""Deterministic comparison of the current and previous workspace snapshots."""

from collections.abc import Iterable
from datetime import datetime

from app.schemas.workspace import (
    EvidenceItem,
    QuoteSummary,
    Statement,
    WorkspaceSection,
    WorkspaceView,
)


def build_what_changed_section(
    quote: QuoteSummary,
    sections: list[WorkspaceSection],
    previous: WorkspaceView | None,
) -> WorkspaceSection:
    """Compare decision-relevant fields with the prior generated workspace."""
    if previous is None:
        return WorkspaceSection(
            id="changes",
            title="What Changed Since the Previous Workspace",
            statements=[
                Statement(
                    text=(
                        "No previous workspace snapshot exists for comparison. Build the workspace "
                        "again after new market or evidence data arrives."
                    ),
                    evidence_ids=(),
                )
            ],
            evidence=[],
        )

    evidence: list[EvidenceItem] = []
    statements: list[Statement] = []
    comparison = _comparison_label(previous.generated_at)

    price_delta = quote.price / previous.quote.price - 1 if previous.quote.price else None
    if price_delta is not None:
        current_id = "current_price"
        previous_id = "previous_snapshot_price"
        evidence.extend(
            [
                EvidenceItem(
                    id=current_id,
                    label="Current workspace price",
                    value=quote.price,
                    display=f"{quote.price:,.2f}",
                    as_of=quote.price_date.isoformat(),
                    source="current workspace quote",
                ),
                EvidenceItem(
                    id=previous_id,
                    label="Previous workspace price",
                    value=previous.quote.price,
                    display=f"{previous.quote.price:,.2f}",
                    as_of=previous.quote.price_date.isoformat(),
                    source=f"workspace snapshot generated {previous.generated_at.isoformat()}",
                ),
            ]
        )
        statements.append(
            Statement(
                text=f"Price is {_signed_pct(price_delta)} versus {comparison}.",
                evidence_ids=(current_id, previous_id),
            )
        )

    current_items = _evidence_map(sections)
    previous_items = _evidence_map(previous.sections)
    for evidence_id, label in (
        ("rsi14", "RSI(14)"),
        ("ema9", "9-day EMA"),
        ("ema21", "21-day EMA"),
    ):
        key = ("technical", evidence_id)
        current = current_items.get(key)
        old = previous_items.get(key)
        if current is None or old is None or current.value is None or old.value is None:
            continue
        current_copy = current.model_copy(update={"id": f"current_{evidence_id}"})
        old_copy = old.model_copy(
            update={
                "id": f"previous_{evidence_id}",
                "source": f"workspace snapshot generated {previous.generated_at.isoformat()}",
            }
        )
        evidence.extend((current_copy, old_copy))
        if evidence_id.startswith("ema"):
            old_distance = previous.quote.price / old.value - 1 if old.value else None
            new_distance = quote.price / current.value - 1 if current.value else None
            if old_distance is None or new_distance is None:
                continue
            text = (
                f"Distance from the {label} is {_signed_pct(new_distance)}, versus "
                f"{_signed_pct(old_distance)} in {comparison}."
            )
        else:
            text = (
                f"{label} is {current.display}, a {current.value - old.value:+.1f}-point "
                f"change from {old.display} in {comparison}."
            )
        statements.append(
            Statement(
                text=text,
                evidence_ids=(current_copy.id, old_copy.id),
            )
        )

    _append_new_evidence_summary(
        statements,
        evidence,
        sections,
        previous.sections,
        section_id="evidence",
        label="company evidence items",
    )
    _append_new_evidence_summary(
        statements,
        evidence,
        sections,
        previous.sections,
        section_id="catalysts",
        label="scheduled catalyst items",
    )

    if not statements:
        statements.append(
            Statement(
                text=f"No comparable decision fields were available in {comparison}.",
                evidence_ids=(),
            )
        )
    return WorkspaceSection(
        id="changes",
        title="What Changed Since the Previous Workspace",
        statements=statements,
        evidence=evidence,
    )


def _append_new_evidence_summary(
    statements: list[Statement],
    output_evidence: list[EvidenceItem],
    current_sections: Iterable[WorkspaceSection],
    previous_sections: Iterable[WorkspaceSection],
    section_id: str,
    label: str,
) -> None:
    current = next((section for section in current_sections if section.id == section_id), None)
    previous = next((section for section in previous_sections if section.id == section_id), None)
    if current is None:
        return
    previous_keys = {_identity(item) for item in previous.evidence} if previous else set()
    new_items = [item for item in current.evidence if _identity(item) not in previous_keys]
    copied = [
        item.model_copy(update={"id": f"new_{section_id}_{index}_{item.id}"})
        for index, item in enumerate(new_items)
    ]
    output_evidence.extend(copied)
    if copied:
        names = "; ".join(item.label for item in copied[:3])
        suffix = f"; plus {len(copied) - 3} more" if len(copied) > 3 else ""
        text = f"{len(copied)} new {label} since the previous workspace: {names}{suffix}."
    else:
        text = f"No new {label} since the previous workspace."
    statements.append(Statement(text=text, evidence_ids=tuple(item.id for item in copied)))


def _evidence_map(sections: Iterable[WorkspaceSection]) -> dict[tuple[str, str], EvidenceItem]:
    return {(section.id, item.id): item for section in sections for item in section.evidence}


def _identity(item: EvidenceItem) -> tuple[str, str, str, str | None]:
    return (item.source, item.label, item.as_of, item.url)


def _comparison_label(generated_at: datetime) -> str:
    return f"the workspace generated at {generated_at.isoformat()}"


def _signed_pct(value: float) -> str:
    return f"{value * 100:+.2f}%"
