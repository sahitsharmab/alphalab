"""Deterministic Decision Board helpers (Layer 1).

Facts only, per ADR-010/011: a *role* is a beta band, a *bracket* is the
nearest EMAs surrounding the current price. Which level is "the trigger" and
which scenario a name fits is deliberate judgment left to the reasoning layer
(Sprint B), never asserted here — this module only reports measured structure.
"""

from collections.abc import Sequence

from app.features import technical as ft

#: Beta bands → role label. Boundaries are inclusive of the lower value.
#: hedge <0 ≤ defensive <0.9 ≤ core <1.5 ≤ high-beta <2.5 ≤ very-high-beta
ROLE_UNCLASSIFIED = "Unclassified"


def role_for_beta(beta: float | None) -> str:
    """Classify a name by its 1-year beta vs the market (SPY)."""
    if beta is None:
        return ROLE_UNCLASSIFIED
    if beta < 0:
        return "Hedge"
    if beta < 0.9:
        return "Defensive"
    if beta < 1.5:
        return "Core"
    if beta < 2.5:
        return "High-beta"
    return "Very high-beta"


#: EMA spans surfaced on the board, shortest → longest.
EMA_SPANS: tuple[tuple[int, str], ...] = (
    (9, "9-EMA"),
    (21, "21-EMA"),
    (50, "50-EMA"),
    (200, "200-EMA"),
)


def ema_ladder(closes: Sequence[float]) -> list[tuple[str, float]]:
    """Compute the available EMAs (some omitted when history is too short)."""
    ladder: list[tuple[str, float]] = []
    for span, label in EMA_SPANS:
        value = ft.ema(closes, span)
        if value is not None:
            ladder.append((label, value))
    return ladder


def bracket(
    price: float, ladder: Sequence[tuple[str, float]]
) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    """Nearest EMA below (support) and above (resistance) the price.

    Returns ``(support, resistance)`` where each is ``(label, value)`` or
    ``None`` when price sits at an extreme of the ladder.
    """
    below = [(label, value) for label, value in ladder if value <= price]
    above = [(label, value) for label, value in ladder if value > price]
    support = max(below, key=lambda item: item[1]) if below else None
    resistance = min(above, key=lambda item: item[1]) if above else None
    return support, resistance
