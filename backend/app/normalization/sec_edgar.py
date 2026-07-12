"""Normalizes SEC EDGAR payloads into evidence records.

Category mapping is deterministic (no AI): the filing form — and for 8-Ks
the item codes — decides the category. Material-event forms only; insider
Forms 3/4/5 and 144 are deliberately excluded for v0.1 (high volume, low
per-item signal — revisit with the Decision Framework).
"""

import json
from datetime import UTC, datetime
from typing import Any

from app.normalization import NormalizationError
from app.schemas.evidence import (
    EntityRef,
    EntityType,
    EvidenceCategory,
    EvidenceRecordIn,
)

#: Forms ingested as evidence in v0.1.
MATERIAL_FORMS = frozenset(
    {"8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "6-K", "DEF 14A", "S-1"}
)

#: 8-K item codes → category (see SEC 8-K item taxonomy).
_ITEM_CATEGORIES: tuple[tuple[str, EvidenceCategory], ...] = (
    ("2.02", EvidenceCategory.EARNINGS),  # Results of operations
    ("1.01", EvidenceCategory.REGULATORY_UPDATE),  # Material agreement
    ("1.02", EvidenceCategory.REGULATORY_UPDATE),  # Agreement termination
    ("3.01", EvidenceCategory.REGULATORY_UPDATE),  # Listing notice
    ("4.01", EvidenceCategory.REGULATORY_UPDATE),  # Accountant change
    ("4.02", EvidenceCategory.REGULATORY_UPDATE),  # Non-reliance (restatement)
    ("5.02", EvidenceCategory.PRESS_RELEASE),  # Officer/director changes
)

_FORM_TITLES = {
    "10-K": "Annual report (10-K)",
    "10-Q": "Quarterly report (10-Q)",
    "20-F": "Annual report (20-F, foreign issuer)",
    "6-K": "Report of foreign issuer (6-K)",
    "DEF 14A": "Proxy statement (DEF 14A)",
    "S-1": "Registration statement (S-1)",
}


def parse_ticker_map(payload_text: str) -> dict[str, str]:
    """Parse company_tickers.json into {TICKER: zero-padded CIK}."""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"sec ticker map: invalid JSON: {exc}") from exc
    mapping: dict[str, str] = {}
    for entry in payload.values():
        ticker = str(entry.get("ticker", "")).upper()
        cik = entry.get("cik_str")
        if ticker and cik is not None:
            mapping[ticker] = f"{int(cik):010d}"
    if not mapping:
        raise NormalizationError("sec ticker map: no entries parsed")
    return mapping


def categorize_filing(form: str, items: str) -> EvidenceCategory:
    """Deterministic category from form type and (for 8-Ks) item codes."""
    if form.startswith("8-K"):
        for code, category in _ITEM_CATEGORIES:
            if code in items:
                return category
        return EvidenceCategory.SEC_FILING
    if form.startswith(("10-K", "10-Q", "20-F")):
        return EvidenceCategory.EARNINGS if form.startswith("10-Q") else EvidenceCategory.SEC_FILING
    return EvidenceCategory.SEC_FILING


def _filing_title(form: str, items: str, primary_doc_description: str) -> str:
    base = _FORM_TITLES.get(form)
    if base is None:
        base = f"SEC filing ({form})"
    if form.startswith("8-K"):
        base = f"Current report (8-K){f' — items {items}' if items else ''}"
    if primary_doc_description and primary_doc_description.lower() not in base.lower():
        base = f"{base}: {primary_doc_description}"
    return base


def parse_submissions(
    payload_text: str, symbol: str, max_records: int = 40
) -> list[EvidenceRecordIn]:
    """Parse a submissions JSON into evidence records (material forms only)."""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"sec submissions: invalid JSON: {exc}") from exc

    recent: dict[str, list[Any]] = (payload.get("filings") or {}).get("recent") or {}
    required = ("form", "accessionNumber", "filingDate", "primaryDocument")
    if not all(key in recent for key in required):
        raise NormalizationError(f"sec submissions: missing columns; got {sorted(recent.keys())!r}")

    cik_raw = payload.get("cik")
    if cik_raw is None:
        raise NormalizationError("sec submissions: missing cik")
    cik = f"{int(cik_raw):010d}"

    forms = recent["form"]
    accessions = recent["accessionNumber"]
    filing_dates = recent["filingDate"]
    acceptance = recent.get("acceptanceDateTime") or [None] * len(forms)
    items_list = recent.get("items") or [""] * len(forms)
    primary_docs = recent["primaryDocument"]
    descriptions = recent.get("primaryDocDescription") or [""] * len(forms)

    records: list[EvidenceRecordIn] = []
    for i, form in enumerate(forms):
        if form not in MATERIAL_FORMS:
            continue
        if len(records) >= max_records:
            break
        accession = str(accessions[i])
        published_at = _parse_published(acceptance[i], str(filing_dates[i]))
        accession_nodash = accession.replace("-", "")
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}"
            f"/{accession_nodash}/{primary_docs[i]}"
        )
        items = str(items_list[i] or "")
        records.append(
            EvidenceRecordIn(
                source_id="sec_edgar",
                external_id=accession,
                category=categorize_filing(form, items),
                title=_filing_title(form, items, str(descriptions[i] or "")),
                url=url,
                published_at=published_at,
                content="",  # full filing text retrieval is a future task
                entities=(EntityRef(entity_type=EntityType.INSTRUMENT, entity_key=symbol),),
                provider_metadata={
                    "form": form,
                    "items": items,
                    "cik": cik,
                    "filing_date": str(filing_dates[i]),
                },
            )
        )
    return records


def _parse_published(acceptance_datetime: Any, filing_date: str) -> datetime:
    """Prefer the exact acceptance moment; fall back to the filing date."""
    if acceptance_datetime:
        try:
            return datetime.fromisoformat(str(acceptance_datetime).replace("Z", "+00:00"))
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(filing_date)
    except ValueError as exc:
        raise NormalizationError(f"sec submissions: invalid filing date {filing_date!r}") from exc
    return parsed.replace(tzinfo=UTC)
