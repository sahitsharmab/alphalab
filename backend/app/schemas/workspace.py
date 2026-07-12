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


class CatalystAssessment(BaseModel):
    """Editorial context for a scheduled event, from the versioned playbook.

    This is deliberately NOT evidence (ADR-011: trust levels measure
    provenance). Importance ratings, transmission chains, and scenarios are
    AlphaLab's own configured judgment — the UI must label them as such and
    keep them visually distinct from evidence rows.
    """

    model_config = ConfigDict(frozen=True)

    playbook_version: str
    kind: str  # playbook key, e.g. "CPI"
    importance: str  # editorial: "very high" | "high" | "medium"
    typical_time_et: str  # editorial, e.g. "08:30 ET"; "" if unknown
    why_it_matters: str
    transmission: tuple[str, ...]  # ordered chain from event to the stock
    watch: tuple[str, ...]  # metrics/instruments to watch on release
    supportive_scenario: str  # conditional hypothesis, never a prediction
    adverse_scenario: str
    horizon: str  # typical reaction window, e.g. "intraday to one week"


class Statement(BaseModel):
    """One conclusion with its supporting evidence references."""

    model_config = ConfigDict(frozen=True)

    text: str
    evidence_ids: tuple[str, ...]
    # Present only on catalyst-timeline statements (ADR-016).
    assessment: CatalystAssessment | None = None


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
