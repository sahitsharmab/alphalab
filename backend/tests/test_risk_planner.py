"""Risk-plan schema and API integration tests."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.risk import RiskPlanRequest


def test_risk_plan_requires_coherent_long_or_short_geometry() -> None:
    with pytest.raises(ValidationError, match="long plans require"):
        RiskPlanRequest(
            symbol="NBIS",
            account_size=Decimal("10000"),
            entry=Decimal("100"),
            invalidation=Decimal("105"),
            target=Decimal("120"),
            max_dollar_risk=Decimal("100"),
        )
