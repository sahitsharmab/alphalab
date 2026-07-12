"""Tests for snapshot-to-snapshot workspace change detection."""

from datetime import UTC, date, datetime

from app.engines.changes import build_what_changed_section
from app.schemas.workspace import (
    EvidenceItem,
    PricePoint,
    QuoteSummary,
    WorkspaceSection,
    WorkspaceView,
)


def _section(section_id: str, items: list[EvidenceItem]) -> WorkspaceSection:
    return WorkspaceSection(id=section_id, title=section_id, statements=[], evidence=items)


def _item(item_id: str, value: float, label: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        label=label or item_id,
        value=value,
        display=f"{value:.1f}",
        as_of="2026-07-10",
        source="test source",
    )


def _view(sections: list[WorkspaceSection]) -> WorkspaceView:
    return WorkspaceView(
        symbol="NBIS",
        name="Nebius",
        currency="USD",
        exchange="NASDAQ",
        generated_at=datetime(2026, 7, 12, 10, tzinfo=UTC),
        quote=QuoteSummary(price=100, price_date=date(2026, 7, 10), change_1d=0.01),
        price_history=[PricePoint(date=date(2026, 7, 10), close=100)],
        sections=sections,
    )


def test_first_workspace_reports_no_comparison() -> None:
    section = build_what_changed_section(
        QuoteSummary(price=101, price_date=date(2026, 7, 10), change_1d=0.01),
        [],
        None,
    )
    assert "No previous workspace snapshot" in section.statements[0].text


def test_changes_metrics_and_new_evidence_with_resolvable_citations() -> None:
    old_evidence = EvidenceItem(
        id="old",
        label="Old filing",
        value=None,
        display="filing",
        as_of="2026-07-09",
        source="SEC EDGAR",
        url="https://example.test/old",
    )
    new_evidence = EvidenceItem(
        id="new",
        label="New filing",
        value=None,
        display="filing",
        as_of="2026-07-10",
        source="SEC EDGAR",
        url="https://example.test/new",
    )
    previous = _view(
        [
            _section("technical", [_item("rsi14", 45), _item("ema9", 98), _item("ema21", 95)]),
            _section("evidence", [old_evidence]),
        ]
    )
    current_sections = [
        _section("technical", [_item("rsi14", 50), _item("ema9", 100), _item("ema21", 96)]),
        _section("evidence", [old_evidence, new_evidence]),
    ]

    section = build_what_changed_section(
        QuoteSummary(price=105, price_date=date(2026, 7, 11), change_1d=0.05),
        current_sections,
        previous,
    )

    texts = " ".join(statement.text for statement in section.statements)
    assert "RSI(14) is 50.0" in texts
    assert "1 new company evidence items" in texts
    known = {item.id for item in section.evidence}
    assert all(set(statement.evidence_ids) <= known for statement in section.statements)
