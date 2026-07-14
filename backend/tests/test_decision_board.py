"""Unit tests for the deterministic Decision Board helpers."""

from app.engines import decision_board as db


def test_role_bands_cover_the_boundaries() -> None:
    assert db.role_for_beta(None) == "Unclassified"
    assert db.role_for_beta(-0.18) == "Hedge"
    assert db.role_for_beta(0.0) == "Defensive"
    assert db.role_for_beta(0.70) == "Defensive"
    assert db.role_for_beta(0.89) == "Defensive"
    assert db.role_for_beta(0.90) == "Core"
    assert db.role_for_beta(1.49) == "Core"
    assert db.role_for_beta(1.50) == "High-beta"
    assert db.role_for_beta(2.49) == "High-beta"
    assert db.role_for_beta(2.50) == "Very high-beta"
    assert db.role_for_beta(3.19) == "Very high-beta"


def test_bracket_finds_nearest_surrounding_emas() -> None:
    ladder = [("9-EMA", 95.0), ("21-EMA", 90.0), ("50-EMA", 105.0), ("200-EMA", 120.0)]
    support, resistance = db.bracket(100.0, ladder)
    assert support == ("9-EMA", 95.0)  # highest EMA at/below price
    assert resistance == ("50-EMA", 105.0)  # lowest EMA above price


def test_bracket_handles_price_at_extremes() -> None:
    ladder = [("9-EMA", 95.0), ("21-EMA", 90.0)]
    support, resistance = db.bracket(100.0, ladder)  # above everything
    assert support == ("9-EMA", 95.0)
    assert resistance is None
    support, resistance = db.bracket(80.0, ladder)  # below everything
    assert support is None
    assert resistance == ("21-EMA", 90.0)


def test_bracket_empty_ladder() -> None:
    assert db.bracket(100.0, []) == (None, None)


def test_ema_ladder_omits_spans_without_enough_history() -> None:
    closes = [100.0 + i * 0.5 for i in range(30)]  # 30 bars: 9/21 yes, 50/200 no
    labels = [label for label, _ in db.ema_ladder(closes)]
    assert "9-EMA" in labels
    assert "21-EMA" in labels
    assert "50-EMA" not in labels
    assert "200-EMA" not in labels
