"""Generic RSS 2.0 → EvidenceRecord normalization.

Feeds are untrusted input: parsed with defusedxml (no external entities),
and item text is stored as data — it never becomes instructions (ADR-006).
"""

import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

from app.normalization import NormalizationError
from app.schemas.evidence import EntityRef, EvidenceCategory, EvidenceRecordIn


def parse_rss(
    payload_text: str,
    source_id: str,
    category: EvidenceCategory,
    entities: tuple[EntityRef, ...],
    max_items: int = 30,
) -> list[EvidenceRecordIn]:
    """Parse one RSS 2.0 feed into evidence records."""
    try:
        root = ElementTree.fromstring(payload_text)
    except ElementTree.ParseError as exc:
        raise NormalizationError(f"{source_id}: invalid RSS XML: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        raise NormalizationError(f"{source_id}: RSS payload has no <channel>")

    records: list[EvidenceRecordIn] = []
    for item in channel.findall("item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue  # tolerate malformed individual items
        published_at = _parse_pub_date(item.findtext("pubDate"), source_id)
        guid = (item.findtext("guid") or "").strip()
        external_id = guid or hashlib.sha256(link.encode("utf-8")).hexdigest()
        description = (item.findtext("description") or "").strip()
        records.append(
            EvidenceRecordIn(
                source_id=source_id,
                external_id=external_id,
                category=category,
                title=title,
                url=link,
                published_at=published_at,
                content=description,
                entities=entities,
                provider_metadata={},
            )
        )
    return records


def _parse_pub_date(raw: str | None, source_id: str) -> datetime:
    if not raw:
        raise NormalizationError(f"{source_id}: RSS item missing pubDate")
    try:
        parsed = parsedate_to_datetime(raw.strip())
    except (TypeError, ValueError) as exc:
        raise NormalizationError(f"{source_id}: invalid pubDate {raw!r}") from exc
    if parsed.tzinfo is None:
        raise NormalizationError(f"{source_id}: pubDate without timezone {raw!r}")
    return parsed
