"""Domain schemas for Evidence (ADR-011, ADR-013).

``EvidenceRecordIn`` is the normalized unit every document-like source
reduces to. Records are never isolated: ``EntityRef`` links tie each
record to typed entities (the relational seed of the Evidence Graph).
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class SourceType(StrEnum):
    """What kind of institution produced the evidence."""

    REGULATOR = "regulator"
    GOVERNMENT = "government"
    COMPANY = "company"
    DATA_PROVIDER = "data_provider"
    MEDIA = "media"
    COMMUNITY = "community"  # Tier 4 — out of scope for v0.1 (ADR-011)


class EvidenceCategory(StrEnum):
    SEC_FILING = "sec_filing"
    PRESS_RELEASE = "press_release"
    EARNINGS = "earnings"
    ANALYST_UPDATE = "analyst_update"
    ECONOMIC_RELEASE = "economic_release"
    REGULATORY_UPDATE = "regulatory_update"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    INDUSTRY_NEWS = "industry_news"
    MARKET_NEWS = "market_news"


class EntityType(StrEnum):
    """Typed entities evidence can reference (ADR-013)."""

    INSTRUMENT = "instrument"  # entity_key = ticker symbol
    SECTOR = "sector"  # entity_key = SIC code
    INDICATOR = "indicator"  # entity_key = series id, e.g. macro series
    EVENT = "event"  # entity_key = event slug, e.g. "fomc-2026-07"
    PERSON = "person"
    PRODUCT = "product"
    TECHNOLOGY = "technology"


class EntityRef(BaseModel):
    """One edge from an evidence record to an entity."""

    model_config = ConfigDict(frozen=True)

    entity_type: EntityType
    entity_key: str
    role: str = "subject"  # e.g. "subject", "mentioned"


class SourceDefinition(BaseModel):
    """Registry entry: who a source is and how much its provenance is trusted.

    Trust measures provenance reliability (is this authentically from the
    stated source?), never interpretive accuracy (ADR-011).
    """

    model_config = ConfigDict(frozen=True)

    source_id: str
    name: str
    source_type: SourceType
    trust_level: int  # 0-10


class EvidenceRecordIn(BaseModel):
    """A normalized evidence record ready for storage."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    external_id: str  # source-scoped stable id (accession number, guid, hash)
    category: EvidenceCategory
    title: str
    url: str
    published_at: datetime
    content: str = ""  # normalized textual content/summary; originals in raw_payloads
    entities: tuple[EntityRef, ...] = ()
    provider_metadata: dict[str, Any] = {}


class EvidenceRecordOut(BaseModel):
    """An evidence record as served to consumers."""

    id: int
    source_id: str
    source_name: str
    source_type: SourceType
    trust_level: int
    category: EvidenceCategory
    title: str
    url: str
    published_at: datetime
    retrieved_at: datetime
    content: str
    entities: list[EntityRef]
    provider_metadata: dict[str, Any]


class EvidenceIngestionReport(BaseModel):
    """Result of one evidence ingestion run."""

    source_id: str
    symbol: str
    records_parsed: int
    records_inserted: int
    retrieved_at: datetime
