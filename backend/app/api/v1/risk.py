"""Deterministic risk-plan endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.risk import RiskPlanAssessment, RiskPlanRequest
from app.services.risk_planner import RiskPlannerError, RiskPlannerService

router = APIRouter(prefix="/risk-plans")
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("")
async def create_risk_plan(request: RiskPlanRequest, session: SessionDep) -> RiskPlanAssessment:
    try:
        return await RiskPlannerService(session).create(request)
    except RiskPlannerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{symbol}/latest")
async def get_latest_risk_plan(symbol: str, session: SessionDep) -> RiskPlanAssessment:
    assessment = await RiskPlannerService(session).latest(symbol.upper())
    if assessment is None:
        raise HTTPException(status_code=404, detail=f"no risk plan exists for {symbol.upper()}")
    return assessment
