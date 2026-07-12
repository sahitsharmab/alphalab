"""The evidence source registry (ADR-011, C1).

Trust levels measure PROVENANCE reliability — "is this authentically from
the stated source?" — never interpretive accuracy. A company press release
is 10/10 authentic and still promotional; skepticism about content is the
job of engines and AI, not this registry.

This registry is deliberate configuration, versioned in git. If per-user
overrides are ever needed, lift these values into settings; the consuming
code only depends on ``get_source`` / ``require_source``.
"""

from app.schemas.evidence import SourceDefinition, SourceType

SOURCES: dict[str, SourceDefinition] = {
    definition.source_id: definition
    for definition in (
        # --- Tier 1: official (facts, not opinions) ---
        SourceDefinition(
            source_id="sec_edgar",
            name="SEC EDGAR",
            source_type=SourceType.REGULATOR,
            trust_level=10,
        ),
        SourceDefinition(
            source_id="federal_reserve",
            name="Federal Reserve",
            source_type=SourceType.GOVERNMENT,
            trust_level=10,
        ),
        SourceDefinition(
            source_id="treasury",
            name="U.S. Treasury",
            source_type=SourceType.GOVERNMENT,
            trust_level=10,
        ),
        SourceDefinition(
            source_id="bls",
            name="Bureau of Labor Statistics",
            source_type=SourceType.GOVERNMENT,
            trust_level=10,
        ),
        SourceDefinition(
            source_id="prnewswire",
            name="PR Newswire (company statements)",
            source_type=SourceType.COMPANY,
            trust_level=10,
        ),
        SourceDefinition(
            source_id="fred",
            name="FRED (St. Louis Fed)",
            source_type=SourceType.DATA_PROVIDER,
            trust_level=9,
        ),
        SourceDefinition(
            source_id="nowflation",
            name="Nowflation",
            source_type=SourceType.DATA_PROVIDER,
            trust_level=9,
        ),
        SourceDefinition(
            source_id="yahoo",
            name="Yahoo Finance",
            source_type=SourceType.DATA_PROVIDER,
            trust_level=8,
        ),
        # --- Tier 2: quality financial media (context, not facts) ---
        SourceDefinition(
            source_id="cnbc",
            name="CNBC",
            source_type=SourceType.MEDIA,
            trust_level=8,
        ),
        SourceDefinition(
            source_id="marketwatch",
            name="MarketWatch",
            source_type=SourceType.MEDIA,
            trust_level=8,
        ),
    )
}


def get_source(source_id: str) -> SourceDefinition | None:
    return SOURCES.get(source_id)


def require_source(source_id: str) -> SourceDefinition:
    source = SOURCES.get(source_id)
    if source is None:
        raise KeyError(
            f"unknown evidence source {source_id!r} — register it in "
            "app/config/evidence_sources.py before ingesting from it"
        )
    return source
