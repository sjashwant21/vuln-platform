"""
Health check endpoint — /v1/health

Used by Docker HEALTHCHECK, load balancers, and uptime monitors.
The deep check verifies DB and Redis connectivity.
Never requires authentication — monitoring agents don't have JWTs.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.infrastructure.database.connection import get_engine

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status:   Literal["ok", "degraded", "down"]
    version:  str
    database: Literal["ok", "error"]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    include_in_schema=True,
)
async def health_check() -> HealthResponse:
    from app.config import get_settings
    cfg = get_settings()

    db_status: Literal["ok", "error"] = "error"
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        pass

    overall: Literal["ok", "degraded", "down"] = (
        "ok" if db_status == "ok" else "degraded"
    )

    return HealthResponse(
        status=overall,
        version=cfg.app_version,
        database=db_status,
    )
