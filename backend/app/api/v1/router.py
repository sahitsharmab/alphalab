"""Aggregate router for API v1."""

from fastapi import APIRouter

from app.api.v1 import evidence, health, macro, workspace

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(macro.router, tags=["macro"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(workspace.router, tags=["workspace"])
