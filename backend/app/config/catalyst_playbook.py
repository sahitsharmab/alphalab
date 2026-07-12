"""The catalyst playbook: editorial context per scheduled-event kind (ADR-016).

Teaches HOW to think about each event: why it matters, the transmission
chain to a stock, what to watch, and conditional scenarios. This is
deliberate, versioned configuration — the same discipline as feature
functions (ADR-008) and prompt templates (ADR-014). It is judgment, not
evidence: the UI labels it with the playbook version and keeps it separate
from evidence rows.

Rules for entries:
* Scenarios are conditional hypotheses ("if X, typically Y"), never
  predictions.
* Instruments used as proxies are named as proxies (QQQ is a Nasdaq-100
  ETF proxy, not "the Nasdaq").
* Typical release times are editorial (FRED publishes dates only).
* Historical per-event sensitivity is NOT here — it requires a real
  point-in-time event study and is reported as "not yet measured" until
  one exists.

Bump PLAYBOOK_VERSION on any content change so persisted workspace
snapshots stay interpretable.
"""

from app.schemas.workspace import CatalystAssessment

PLAYBOOK_VERSION = "1.1.0"


def _entry(
    kind: str,
    importance: str,
    typical_time_et: str,
    why_it_matters: str,
    transmission: tuple[str, ...],
    watch: tuple[str, ...],
    supportive_scenario: str,
    adverse_scenario: str,
    horizon: str,
) -> CatalystAssessment:
    return CatalystAssessment(
        playbook_version=PLAYBOOK_VERSION,
        kind=kind,
        importance=importance,
        typical_time_et=typical_time_et,
        why_it_matters=why_it_matters,
        transmission=transmission,
        watch=watch,
        supportive_scenario=supportive_scenario,
        adverse_scenario=adverse_scenario,
        horizon=horizon,
    )


PLAYBOOK: dict[str, CatalystAssessment] = {
    entry.kind: entry
    for entry in (
        _entry(
            kind="CPI",
            importance="very high",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "The market's primary inflation reading. It sets expectations for "
                "the Federal Reserve's policy path and re-prices long-duration "
                "assets within minutes of release."
            ),
            transmission=(
                "Inflation surprise",
                "Fed rate expectations",
                "US 10-year Treasury yield",
                "Equity valuation multiples",
                "High-beta growth stocks",
            ),
            watch=(
                "US 10-year Treasury yield",
                "Fed funds futures (rate-path repricing)",
                "QQQ (Nasdaq-100 ETF proxy)",
                "VIX",
            ),
            supportive_scenario=(
                "Inflation comes in softer than consensus while growth expectations "
                "hold — yields typically ease and valuation multiples expand."
            ),
            adverse_scenario=(
                "An upside inflation surprise pushes yields higher — high-valuation "
                "and high-beta names typically de-rate fastest."
            ),
            horizon="Intraday to one week",
        ),
        _entry(
            kind="PPI",
            importance="high",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "Measures prices producers receive — a leading input to future "
                "consumer inflation and corporate margins. Usually a smaller market "
                "event than CPI, but it reinforces or challenges the CPI narrative."
            ),
            transmission=(
                "Producer-price surprise",
                "Pipeline inflation expectations",
                "Treasury yields",
                "Margin and multiple expectations",
            ),
            watch=(
                "US 10-year Treasury yield",
                "QQQ (Nasdaq-100 ETF proxy)",
                "The prior CPI print (does PPI confirm or contradict it?)",
            ),
            supportive_scenario="Soft producer prices confirming a disinflation trend.",
            adverse_scenario=(
                "Hot producer prices on the heels of a hot CPI — compounds the "
                "tightening narrative."
            ),
            horizon="Intraday to a few days",
        ),
        _entry(
            kind="EMPLOYMENT",
            importance="very high",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "The jobs report reads the labor market: payrolls, unemployment, "
                "and wage growth. It moves rate expectations from the growth side — "
                "strong wages can mean sticky inflation; weak payrolls can mean "
                "slowdown."
            ),
            transmission=(
                "Payrolls/wages surprise",
                "Growth and rate expectations",
                "Treasury yields",
                "Cyclical vs defensive rotation",
                "Broad risk appetite",
            ),
            watch=(
                "Nonfarm payrolls vs consensus",
                "Average hourly earnings",
                "US 2-year Treasury yield (policy-sensitive)",
                "SPY and QQQ (index ETF proxies)",
            ),
            supportive_scenario=(
                "Cooling-but-not-collapsing labor data — enough softness to ease "
                "rate pressure without stoking recession fear."
            ),
            adverse_scenario=(
                "Either extreme: hot wage growth (rate fears) or sharply negative "
                "payrolls (growth fears)."
            ),
            horizon="Intraday to one week",
        ),
        _entry(
            kind="RETAIL_SALES",
            importance="medium",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "Consumer spending drives most of US GDP. The market reaction is "
                "context-dependent: strength supports growth but can feed inflation "
                "worry; weakness raises slowdown concern but can support easing hopes."
            ),
            transmission=(
                "Spending surprise",
                "GDP growth expectations",
                "Rate expectations",
                "Consumer and cyclical sectors",
                "Broad risk sentiment",
            ),
            watch=(
                "Headline vs control-group retail sales",
                "US 10-year Treasury yield",
                "Consumer discretionary vs staples relative move",
            ),
            supportive_scenario="Moderate spending growth consistent with a soft landing.",
            adverse_scenario=(
                "A sharp miss amplifying recession concern, or a hot print amplifying "
                "inflation concern — the prevailing narrative decides which."
            ),
            horizon="Intraday to a few days",
        ),
        _entry(
            kind="GDP",
            importance="high",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "The broadest growth reading. Often backward-looking by release "
                "time, but large surprises reset the growth narrative and earnings "
                "expectations."
            ),
            transmission=(
                "Growth surprise",
                "Earnings expectations",
                "Rate expectations",
                "Equity risk premium",
            ),
            watch=(
                "Headline GDP vs consensus",
                "Core PCE within the GDP report",
                "US 10-year Treasury yield",
            ),
            supportive_scenario="Growth near trend with cooling inflation components.",
            adverse_scenario=(
                "Contraction (recession narrative) or hot growth plus hot prices "
                "(higher-for-longer narrative)."
            ),
            horizon="One day to one week",
        ),
        _entry(
            kind="PCE",
            importance="high",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "Personal Income and Outlays contains PCE inflation — the Federal "
                "Reserve's preferred inflation gauge, the one its target is defined "
                "on."
            ),
            transmission=(
                "Core PCE surprise",
                "Fed policy-path expectations",
                "Treasury yields",
                "Valuation multiples",
            ),
            watch=(
                "Core PCE month-over-month vs consensus",
                "US 10-year Treasury yield",
                "Fed funds futures",
            ),
            supportive_scenario=("Core PCE at or below the path consistent with the Fed's target."),
            adverse_scenario="Core PCE re-accelerating — undercuts easing expectations.",
            horizon="Intraday to one week",
        ),
        _entry(
            kind="CONSUMER_SENTIMENT",
            importance="medium",
            typical_time_et="10:00 ET",
            why_it_matters=(
                "The University of Michigan survey pairs consumer confidence with "
                "one of the most-watched inflation-expectations readings — the Fed "
                "treats expectations as an input to actual inflation. Timing note: "
                "this timeline shows the scheduled FINAL release (via FRED); the "
                "market-moving preliminary reading lands roughly two weeks earlier "
                "and has no free schedule source."
            ),
            transmission=(
                "Inflation-expectations surprise",
                "Fed credibility and policy expectations",
                "Treasury yields",
                "Risk sentiment",
            ),
            watch=(
                "1-year and 5-10-year inflation expectations",
                "Sentiment index vs consensus",
            ),
            supportive_scenario="Anchored inflation expectations with stable sentiment.",
            adverse_scenario=(
                "Rising long-run inflation expectations — pressures the Fed toward hawkishness."
            ),
            horizon="Intraday",
        ),
        _entry(
            kind="EMPIRE_STATE",
            importance="medium",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "The first regional manufacturing survey of each month (NY Fed) — "
                "a timely but volatile preview of national manufacturing momentum "
                "ahead of the ISM reading."
            ),
            transmission=(
                "Regional activity surprise",
                "National manufacturing expectations",
                "Growth narrative",
                "Cyclical vs defensive sentiment",
            ),
            watch=(
                "Headline index vs consensus",
                "New orders component",
                "Prices paid (inflation pressure signal)",
            ),
            supportive_scenario="Rebounding new orders with easing prices paid.",
            adverse_scenario=(
                "Sharp contraction reinforcing slowdown fears, or hot prices paid "
                "reinforcing inflation fears."
            ),
            horizon="Intraday",
        ),
        _entry(
            kind="PHILLY_FED",
            importance="medium",
            typical_time_et="08:30 ET",
            why_it_matters=(
                "A timely read on Mid-Atlantic manufacturing. Alone it rarely moves "
                "indexes, but paired with the Empire State survey it shapes "
                "expectations for the national ISM print and colors the growth "
                "narrative in data-heavy weeks."
            ),
            transmission=(
                "Regional activity surprise",
                "National manufacturing expectations (ISM)",
                "Growth narrative",
                "Industrial/cyclical sentiment",
            ),
            watch=(
                "Headline index vs consensus",
                "New orders and prices-paid components",
                "Reaction in industrials and cyclicals",
            ),
            supportive_scenario=(
                "Improving orders with easing prices paid — growth without renewed "
                "inflation pressure."
            ),
            adverse_scenario=(
                "Contraction plus rising prices paid — a stagflation-flavored reading."
            ),
            horizon="Intraday",
        ),
        _entry(
            kind="FOMC_MEETING",
            importance="very high",
            typical_time_et="14:00 ET (press conference 14:30 ET)",
            why_it_matters=(
                "The rate decision and forward guidance set the discount rate for "
                "every asset. Statement wording and the press conference often move "
                "markets more than the decision itself."
            ),
            transmission=(
                "Policy decision and guidance",
                "Full yield curve",
                "Dollar and financial conditions",
                "Equity multiples and risk appetite",
            ),
            watch=(
                "Statement language changes vs the prior meeting",
                "Dot plot / economic projections (quarterly meetings)",
                "US 2-year Treasury yield (policy-sensitive)",
                "Press-conference tone",
            ),
            supportive_scenario="Policy path in line with, or easier than, market pricing.",
            adverse_scenario=(
                "A hawkish surprise versus market pricing — guidance matters more "
                "than the move itself."
            ),
            horizon="Intraday to several weeks",
        ),
        _entry(
            kind="FOMC_MINUTES",
            importance="medium",
            typical_time_et="14:00 ET",
            why_it_matters=(
                "The detailed record of the last FOMC meeting. Markets read it for "
                "the balance of views behind the decision and hints about the "
                "committee's reaction function."
            ),
            transmission=(
                "Committee-tone surprise",
                "Rate expectations",
                "Treasury yields",
                "Risk sentiment",
            ),
            watch=(
                "Rate-path repricing after release",
                "US 2-year Treasury yield",
            ),
            supportive_scenario="Minutes read softer than the meeting-day interpretation.",
            adverse_scenario=(
                "Minutes revealing broader support for tightening than the market assumed."
            ),
            horizon="Intraday",
        ),
        _entry(
            kind="BEIGE_BOOK",
            importance="medium",
            typical_time_et="14:00 ET",
            why_it_matters=(
                "Anecdotal economic conditions across the twelve Fed districts, "
                "published ahead of each FOMC meeting. Rarely a large market event, "
                "but it shapes the meeting's economic backdrop."
            ),
            transmission=(
                "Regional-conditions narrative",
                "Expectations for the next FOMC meeting",
            ),
            watch=("Language on pricing power and labor availability",),
            supportive_scenario="Districts reporting easing price pressures.",
            adverse_scenario="Districts reporting re-accelerating costs and wages.",
            horizon="Days (via the next FOMC meeting)",
        ),
    )
}


def get_assessment(kind: str) -> CatalystAssessment | None:
    return PLAYBOOK.get(kind)
