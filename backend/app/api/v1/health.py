"""
Health check endpoint — /v1/health

Used by Docker HEALTHCHECK, load balancers, and uptime monitors.
The deep check verifies DB and Redis connectivity.
Never requires authentication — monitoring agents don't have JWTs.
"""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from app.dependencies import get_current_user
from app.infrastructure.database.connection import get_engine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


class MinimalHealthResponse(BaseModel):
    status: Literal["ok"]


class DetailedHealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    database: Literal["ok", "error"]


@router.get(
    "/health",
    response_model=MinimalHealthResponse,
    summary="Minimal system health check (public)",
)
async def health_check() -> MinimalHealthResponse:
    """Minimal health check for load balancers. Does not leak info."""
    return MinimalHealthResponse(status="ok")


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed system health check (internal)",
    dependencies=[Depends(get_current_user)],
)
async def health_detailed() -> DetailedHealthResponse:
    """Detailed health check revealing DB status and version info. Requires auth."""
    from app.config import get_settings

    cfg = get_settings()

    db_status: Literal["ok", "error"] = "error"
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.warning("health_check_db_failed", error=str(e))

    overall: Literal["ok", "degraded", "down"] = "ok" if db_status == "ok" else "degraded"

    return DetailedHealthResponse(
        status=overall,
        version=cfg.app_version,
        database=db_status,
    )
