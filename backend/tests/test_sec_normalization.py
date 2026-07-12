"""Unit tests for SEC EDGAR normalization and category mapping."""

import json

import pytest

from app.normalization import NormalizationError
from app.normalization.sec_edgar import (
    categorize_filing,
    parse_submissions,
    parse_ticker_map,
)
from app.schemas.evidence import EntityType, EvidenceCategory


def make_submissions_json(
    forms: list[str],
    items: list[str] | None = None,
    cik: int = 723125,
) -> str:
    n = len(forms)
    return json.dumps(
        {
            "cik": cik,
            "name": "Micron Technology Inc",
            "filings": {
                "recent": {
                    "form": forms,
                    "accessionNumber": [f"0000723125-26-{i:06d}" for i in range(n)],
                    "filingDate": ["2026-07-01"] * n,
                    "acceptanceDateTime": ["2026-07-01T16:30:12.000Z"] * n,
                    "items": items or [""] * n,
                    "primaryDocument": [f"doc{i}.htm" for i in range(n)],
                    "primaryDocDescription": ["Report"] * n,
                }
            },
        }
    )


def test_parse_ticker_map() -> None:
    payload = json.dumps(
        {
            "0": {"cik_str": 723125, "ticker": "MU", "title": "MICRON TECHNOLOGY INC"},
            "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }
    )
    mapping = parse_ticker_map(payload)
    assert mapping["MU"] == "0000723125"
    assert mapping["AAPL"] == "0000320193"


def test_parse_ticker_map_rejects_garbage() -> None:
    with pytest.raises(NormalizationError):
        parse_ticker_map("<html>blocked</html>")
    with pytest.raises(NormalizationError, match="no entries"):
        parse_ticker_map("{}")


def test_category_mapping_is_deterministic() -> None:
    assert categorize_filing("8-K", "2.02,9.01") is EvidenceCategory.EARNINGS
    assert categorize_filing("8-K", "1.01") is EvidenceCategory.REGULATORY_UPDATE
    assert categorize_filing("8-K", "5.02") is EvidenceCategory.PRESS_RELEASE
    assert categorize_filing("8-K", "7.01") is EvidenceCategory.SEC_FILING
    assert categorize_filing("10-Q", "") is EvidenceCategory.EARNINGS
    assert categorize_filing("10-K", "") is EvidenceCategory.SEC_FILING
    assert categorize_filing("DEF 14A", "") is EvidenceCategory.SEC_FILING


def test_parse_submissions_filters_to_material_forms() -> None:
    payload = make_submissions_json(
        forms=["8-K", "4", "10-Q", "144", "SC 13G/A", "10-K"],
        items=["2.02,9.01", "", "", "", "", ""],
    )
    records = parse_submissions(payload, "MU")

    assert [r.provider_metadata["form"] for r in records] == ["8-K", "10-Q", "10-K"]
    assert records[0].category is EvidenceCategory.EARNINGS
    assert records[0].source_id == "sec_edgar"
    assert records[0].url.startswith("https://www.sec.gov/Archives/edgar/data/723125/")
    assert records[0].published_at.tzinfo is not None
    # Evidence Graph seed: every record links to the instrument (ADR-013).
    assert any(
        e.entity_type is EntityType.INSTRUMENT and e.entity_key == "MU" for e in records[0].entities
    )


def test_parse_submissions_missing_columns_raises() -> None:
    with pytest.raises(NormalizationError, match="missing columns"):
        parse_submissions(json.dumps({"cik": 1, "filings": {"recent": {"form": []}}}), "MU")
