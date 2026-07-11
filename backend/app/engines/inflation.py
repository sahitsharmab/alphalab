"""Inflation Engine: classifies the inflation environment from the
Nowflation headline gauge (Sprint A6).

Deterministic thresholds, documented here and cited in the statements:

* Regime by YoY level: low < 2% ≤ moderate ≤ 4% < high
  (2% mirrors the Fed target; 4% marks historically restrictive territory).
* Trend by 3-month change in YoY: rising > +0.25pp, falling < -0.25pp,
  otherwise stable.
"""

from datetime import date, timedelta

from app.schemas.macro import MacroObservationOut
from app.schemas.workspace import EvidenceItem, Statement, WorkspaceSection

REGIME_LOW_BELOW = 0.02
REGIME_HIGH_ABOVE = 0.04
TREND_THRESHOLD_PP = 0.0025  # 0.25 percentage points over 3 months


def _pp(value: float) -> str:
    return f"{value * 100:+.2f}pp"


def _value_on_or_before(
    observations: list[MacroObservationOut], target: date
) -> MacroObservationOut | None:
    candidate = None
    for obs in observations:
        if obs.observation_date <= target:
            candidate = obs
        else:
            break
    return candidate


def build_macro_section(yoy: list[MacroObservationOut]) -> WorkspaceSection:
    """Inflation level, regime, and trend — the macro backdrop for a decision."""
    statements: list[Statement] = []
    evidence: list[EvidenceItem] = []

    if not yoy:
        return WorkspaceSection(
            id="macro",
            title="Macro Environment",
            statements=[
                Statement(
                    text=(
                        "No inflation data ingested yet — run the Nowflation "
                        "ingestion to populate the macro backdrop."
                    ),
                    evidence_ids=(),
                )
            ],
            evidence=[],
        )

    latest = yoy[-1]
    latest_value = float(latest.value)
    as_of = latest.observation_date.isoformat()
    source = "nowflation.headline.yoy"

    evidence.append(
        EvidenceItem(
            id="yoy_now",
            label="Inflation YoY (Nowflation gauge)",
            value=latest_value,
            display=f"{latest_value * 100:.2f}%",
            as_of=as_of,
            source=source,
        )
    )

    if latest_value < REGIME_LOW_BELOW:
        regime, implication = "low", "a generally supportive backdrop for risk assets"
    elif latest_value <= REGIME_HIGH_ABOVE:
        regime, implication = "moderate", "a backdrop that keeps policy in focus"
    else:
        regime, implication = "high", "a restrictive backdrop that pressures valuations"
    statements.append(
        Statement(
            text=(
                f"Inflation regime is {regime}: the market-price gauge runs at "
                f"{latest_value * 100:.2f}% year over year (regime bands: "
                f"low <2%, moderate 2-4%, high >4%) — {implication}."
            ),
            evidence_ids=("yoy_now",),
        )
    )

    three_months_ago = _value_on_or_before(yoy, latest.observation_date - timedelta(days=91))
    if three_months_ago is not None:
        change = latest_value - float(three_months_ago.value)
        evidence.append(
            EvidenceItem(
                id="yoy_3m_ago",
                label=f"Inflation YoY on {three_months_ago.observation_date.isoformat()}",
                value=float(three_months_ago.value),
                display=f"{float(three_months_ago.value) * 100:.2f}%",
                as_of=three_months_ago.observation_date.isoformat(),
                source=source,
            )
        )
        evidence.append(
            EvidenceItem(
                id="yoy_3m_change",
                label="3-month change in YoY",
                value=change,
                display=_pp(change),
                as_of=as_of,
                source=source,
            )
        )
        if change > TREND_THRESHOLD_PP:
            direction = "rising"
            note = "re-acceleration raises the odds of tighter policy"
        elif change < -TREND_THRESHOLD_PP:
            direction = "falling"
            note = "disinflation historically eases pressure on multiples"
        else:
            direction = "stable"
            note = "little pressure on the policy outlook from this reading"
        statements.append(
            Statement(
                text=(
                    f"Inflation is {direction}: {_pp(change)} over the past three months "
                    f"(threshold ±0.25pp) — {note}."
                ),
                evidence_ids=("yoy_now", "yoy_3m_ago", "yoy_3m_change"),
            )
        )

    statements.append(
        Statement(
            text=(
                "This gauge is a daily market-price nowcast (not the official CPI); "
                "it typically leads official prints but can diverge from them."
            ),
            evidence_ids=("yoy_now",),
        )
    )

    return WorkspaceSection(
        id="macro", title="Macro Environment", statements=statements, evidence=evidence
    )
