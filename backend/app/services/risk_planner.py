"""Risk-plan orchestration over stored daily market and catalyst data."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.features import technical as ft
from app.models.risk import RiskPlan
from app.repositories.calendar import CalendarEventRepository
from app.repositories.market import MarketBarRepository
from app.repositories.risk import RiskPlanRepository
from app.schemas.risk import RiskPlanAssessment, RiskPlanRequest, TradeDirection


class RiskPlannerError(Exception):
    """Raised when stored evidence is insufficient for a risk assessment."""


class RiskPlannerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bars = MarketBarRepository(session)
        self._calendar = CalendarEventRepository(session)
        self._plans = RiskPlanRepository(session)

    async def create(self, request: RiskPlanRequest) -> RiskPlanAssessment:
        symbol = request.symbol.upper()
        bars = await self._bars.get_bars(symbol)
        if not bars:
            raise RiskPlannerError(f"build the {symbol} workspace before creating a risk plan")

        risk_per_share = abs(request.entry - request.invalidation)
        reward_per_share = abs(request.target - request.entry)
        maximum_shares = int(
            (request.max_dollar_risk / risk_per_share).to_integral_value(rounding=ROUND_FLOOR)
        )
        position_value = request.entry * maximum_shares
        account_exposure_pct = position_value / request.account_size * 100
        account_risk_pct = request.max_dollar_risk / request.account_size * 100
        risk_reward = reward_per_share / risk_per_share
        direction = (
            TradeDirection.LONG if request.invalidation < request.entry else TradeDirection.SHORT
        )

        closes = [float(bar.adj_close) for bar in bars]
        atr_fraction = ft.atr_fraction(
            [float(bar.high) for bar in bars],
            [float(bar.low) for bar in bars],
            closes,
        )
        atr = Decimal(str(atr_fraction * closes[-1])) if atr_fraction is not None else None
        distance_atr = risk_per_share / atr if atr and atr > 0 else None
        drawdown = ft.max_drawdown(closes)
        drawdown_decimal = Decimal(str(drawdown)) if drawdown is not None else None

        warnings: list[str] = []
        if maximum_shares == 0:
            warnings.append("Risk budget is smaller than the risk on one share.")
        if account_exposure_pct > 100:
            warnings.append("Calculated position value exceeds the stated account size.")
        if distance_atr is not None and distance_atr < 1:
            warnings.append(
                "The selected invalidation is inside one daily ATR; ordinary volatility "
                "may reach it."
            )
        upcoming = await self._calendar.list_upcoming(datetime.now(UTC).date(), limit=40)
        cutoff = datetime.now(UTC).date() + timedelta(days=7)
        near_events = [event for event in upcoming if event.scheduled_on <= cutoff]
        if near_events:
            names = ", ".join(f"{event.title} ({event.scheduled_on})" for event in near_events[:3])
            warnings.append(f"Upcoming seven-day catalyst risk: {names}.")

        assumptions = (
            "Position size is a maximum under the user-selected dollar-risk budget, "
            "not a recommendation.",
            "The invalidation level is user-defined; AlphaLab does not claim it is "
            "objectively correct.",
            "ATR and drawdown use stored daily bars and cannot capture overnight gap "
            "magnitude in advance.",
        )
        payload = {
            "direction": direction.value,
            "dollar_risk_per_share": str(risk_per_share),
            "maximum_shares": maximum_shares,
            "position_value": str(position_value),
            "account_exposure_pct": str(account_exposure_pct),
            "account_risk_pct": str(account_risk_pct),
            "reward_per_share": str(reward_per_share),
            "risk_reward_ratio": str(risk_reward),
            "atr_per_share": str(atr) if atr is not None else None,
            "invalidation_distance_atr": str(distance_atr) if distance_atr is not None else None,
            "max_drawdown_1y": str(drawdown_decimal) if drawdown_decimal is not None else None,
            "warnings": warnings,
            "assumptions": list(assumptions),
        }
        plan = RiskPlan(
            symbol=symbol,
            account_size=request.account_size,
            entry=request.entry,
            invalidation=request.invalidation,
            target=request.target,
            max_dollar_risk=request.max_dollar_risk,
            assessment=payload,
        )
        self._plans.add(plan)
        await self._session.commit()
        await self._session.refresh(plan)
        return _to_assessment(plan)

    async def latest(self, symbol: str) -> RiskPlanAssessment | None:
        plan = await self._plans.latest(symbol)
        return _to_assessment(plan) if plan is not None else None


def _to_assessment(plan: RiskPlan) -> RiskPlanAssessment:
    payload = plan.assessment
    return RiskPlanAssessment(
        id=plan.id,
        symbol=plan.symbol,
        direction=TradeDirection(payload["direction"]),
        account_size=plan.account_size,
        entry=plan.entry,
        invalidation=plan.invalidation,
        target=plan.target,
        max_dollar_risk=plan.max_dollar_risk,
        dollar_risk_per_share=Decimal(payload["dollar_risk_per_share"]),
        maximum_shares=int(payload["maximum_shares"]),
        position_value=Decimal(payload["position_value"]),
        account_exposure_pct=Decimal(payload["account_exposure_pct"]),
        account_risk_pct=Decimal(payload["account_risk_pct"]),
        reward_per_share=Decimal(payload["reward_per_share"]),
        risk_reward_ratio=Decimal(payload["risk_reward_ratio"]),
        atr_per_share=Decimal(payload["atr_per_share"]) if payload["atr_per_share"] else None,
        invalidation_distance_atr=(
            Decimal(payload["invalidation_distance_atr"])
            if payload["invalidation_distance_atr"]
            else None
        ),
        max_drawdown_1y=(
            Decimal(payload["max_drawdown_1y"]) if payload["max_drawdown_1y"] else None
        ),
        warnings=tuple(payload["warnings"]),
        assumptions=tuple(payload["assumptions"]),
        created_at=plan.created_at,
    )
