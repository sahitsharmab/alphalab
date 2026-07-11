"""Aggregate router for API v1."""

from fastapi import APIRouter

from app.api.v1 import health, macro

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(macro.router, tags=["macro"])
