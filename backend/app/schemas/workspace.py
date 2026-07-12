"""The Investment Workspace contract (ADR-010).

Evidence is first-class: sections contain statements, and every statement
references machine-readable evidence items. The UI renders statements
expandable to their evidence; future interactive capabilities (notes,
drill-downs, follow-up questions) attach to these objects.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator


class EvidenceItem(BaseModel):
    """One verifiable data point backing a statement."""

    model_config = ConfigDict(frozen=True)

    id: str  # stable within the section, e.g. "rsi14"
    label: str  # "RSI (14-day)"
    value: float | None  # machine-readable value where meaningful
    display: str  # human-readable rendering, e.g. "31.7"
    as_of: str  # date the underlying data describes (ISO)
    source: str  # provenance, e.g. "yahoo:MU daily bars"
    trust_level: int | None = None  # source trust 0-10 where known (ADR-011)
    url: str | None = None  # link to the original document where one exists


class Statement(BaseModel):
    """One conclusion with its supporting evidence references."""

    model_config = ConfigDict(frozen=True)

    text: str
    evidence_ids: tuple[str, ...]


class WorkspaceSection(BaseModel):
    """A titled group of statements plus the evidence they cite."""

    id: str  # "technical" | "historical" | "macro" | ...
    title: str
    statements: list[Statement]
    evidence: list[EvidenceItem]

    @model_validator(mode="after")
    def evidence_ids_resolve(self) -> "WorkspaceSection":
        """Every cited evidence id must exist — traceability is the contract."""
        known = {item.id for item in self.evidence}
        for statement in self.statements:
            missing = set(statement.evidence_ids) - known
            if missing:
                raise ValueError(
                    f"section {self.id!r}: statement cites unknown evidence {sorted(missing)}"
                )
        return self


class PricePoint(BaseModel):
    date: date
    close: float


class QuoteSummary(BaseModel):
    """Latest price context for the workspace header."""

    price: float
    price_date: date
    change_1d: float | None  # fraction, e.g. -0.012


class WorkspaceView(BaseModel):
    """Everything the workspace page needs for one symbol."""

    symbol: str
    name: str
    currency: str
    exchange: str
    generated_at: datetime
    quote: QuoteSummary
    price_history: list[PricePoint]  # ~1 year of daily closes for the chart
    sections: list[WorkspaceSection]
