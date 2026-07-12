"""Unit tests for generic RSS normalization and the evidence engine."""

from datetime import UTC, datetime

import pytest

from app.engines.evidence import build_company_evidence_section
from app.normalization import NormalizationError
from app.normalization.rss import parse_rss
from app.schemas.evidence import (
    EntityRef,
    EntityType,
    EvidenceCategory,
    EvidenceRecordOut,
    SourceType,
)

ENTITIES = (EntityRef(entity_type=EntityType.INSTRUMENT, entity_key="MU", role="mentioned"),)


def make_rss(items: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"<item><title>{title}</title><link>{link}</link>"
        f"<pubDate>{pub}</pubDate><guid>{link}</guid></item>"
        for title, link, pub in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{body}</channel></rss>'


def test_parse_rss_items() -> None:
    payload = make_rss(
        [
            ("MU beats estimates", "https://example.com/a", "Sat, 11 Jul 2026 19:00:00 +0000"),
            ("Semis rally", "https://example.com/b", "Sat, 11 Jul 2026 18:00:00 GMT"),
        ]
    )
    records = parse_rss(payload, "yahoo_news", EvidenceCategory.MARKET_NEWS, ENTITIES)

    assert len(records) == 2
    assert records[0].title == "MU beats estimates"
    assert records[0].external_id == "https://example.com/a"
    assert records[0].published_at.tzinfo is not None
    assert records[0].entities[0].role == "mentioned"


def test_parse_rss_skips_incomplete_items_but_rejects_garbage() -> None:
    payload = make_rss([("Titled", "https://example.com/a", "Sat, 11 Jul 2026 19:00:00 +0000")])
    payload = payload.replace("<channel>", "<channel><item><title>No link</title></item>", 1)
    records = parse_rss(payload, "yahoo_news", EvidenceCategory.MARKET_NEWS, ENTITIES)
    assert len(records) == 1  # incomplete item tolerated

    with pytest.raises(NormalizationError, match="invalid RSS XML"):
        parse_rss("not xml at all", "yahoo_news", EvidenceCategory.MARKET_NEWS, ENTITIES)
    with pytest.raises(NormalizationError, match="no <channel>"):
        parse_rss("<rss version='2.0'></rss>", "yahoo_news", EvidenceCategory.MARKET_NEWS, ENTITIES)


def _record(
    record_id: int,
    source_id: str,
    source_type: SourceType,
    trust: int,
    category: EvidenceCategory,
    title: str,
    published: datetime,
) -> EvidenceRecordOut:
    return EvidenceRecordOut(
        id=record_id,
        source_id=source_id,
        source_name=source_id,
        source_type=source_type,
        trust_level=trust,
        category=category,
        title=title,
        url=f"https://example.com/{record_id}",
        published_at=published,
        retrieved_at=published,
        content="",
        entities=[],
        provider_metadata={},
    )


def test_company_evidence_section_statements_and_trust() -> None:
    now = datetime.now(UTC)
    records = [
        _record(
            1,
            "sec_edgar",
            SourceType.REGULATOR,
            10,
            EvidenceCategory.EARNINGS,
            "Quarterly report (10-Q)",
            now,
        ),
        _record(
            2,
            "sec_edgar",
            SourceType.REGULATOR,
            10,
            EvidenceCategory.SEC_FILING,
            "Current report (8-K)",
            now,
        ),
        _record(
            3,
            "yahoo_news",
            SourceType.MEDIA,
            7,
            EvidenceCategory.MARKET_NEWS,
            "Semis rally on AI demand",
            now,
        ),
    ]

    section = build_company_evidence_section(records)

    assert section.id == "evidence"
    texts = " ".join(s.text for s in section.statements)
    assert "SEC filing" in texts
    assert "Latest earnings-related filing" in texts
    assert "aggregated commentary (trust 7/10)" in texts
    # Every evidence item carries trust + url for the UI (ADR-011/010).
    assert all(item.trust_level is not None and item.url for item in section.evidence)


def test_company_evidence_section_empty() -> None:
    section = build_company_evidence_section([])
    assert "No evidence records" in section.statements[0].text
