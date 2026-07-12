"""Storage access for permanent user risk-plan artifacts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import RiskPlan


class RiskPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, plan: RiskPlan) -> None:
        self._session.add(plan)

    async def latest(self, symbol: str) -> RiskPlan | None:
        result: RiskPlan | None = await self._session.scalar(
            select(RiskPlan)
            .where(RiskPlan.symbol == symbol.upper())
            .order_by(RiskPlan.created_at.desc(), RiskPlan.id.desc())
            .limit(1)
        )
        return result
