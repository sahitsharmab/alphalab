"""User-owned trade-risk plans and deterministic assessments."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class RiskPlanRequest(BaseModel):
    """Inputs selected by the user; AlphaLab does not choose invalidation levels."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1, max_length=16)
    account_size: Decimal = Field(gt=0)
    entry: Decimal = Field(gt=0)
    invalidation: Decimal = Field(gt=0)
    target: Decimal = Field(gt=0)
    max_dollar_risk: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def coherent_trade_geometry(self) -> "RiskPlanRequest":
        long_plan = self.invalidation < self.entry < self.target
        short_plan = self.target < self.entry < self.invalidation
        if not long_plan and not short_plan:
            raise ValueError(
                "long plans require invalidation < entry < target; short plans require "
                "target < entry < invalidation"
            )
        return self


class RiskPlanAssessment(BaseModel):
    """Calculated risk context, never an instruction or objectively correct stop."""

    model_config = ConfigDict(frozen=True)

    id: int
    symbol: str
    direction: TradeDirection
    account_size: Decimal
    entry: Decimal
    invalidation: Decimal
    target: Decimal
    max_dollar_risk: Decimal
    dollar_risk_per_share: Decimal
    maximum_shares: int
    position_value: Decimal
    account_exposure_pct: Decimal
    account_risk_pct: Decimal
    reward_per_share: Decimal
    risk_reward_ratio: Decimal
    atr_per_share: Decimal | None
    invalidation_distance_atr: Decimal | None
    max_drawdown_1y: Decimal | None
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    created_at: datetime
