"""Dashboard API router — /v1/dashboard/*"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.dashboard_schemas import DashboardSummaryResponse, HealthScoreResponse
from app.api.schemas.scan_schemas import ScanJobResponse
from app.application.services.dashboard_service import DashboardService
from app.dependencies import CurrentUser, get_db_session

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Dashboard summary")
async def get_summary(current_user: CurrentUser, db: DBSession) -> DashboardSummaryResponse:
    """Returns aggregate counts and the 5 most recent scans."""
    svc = DashboardService(db)
    data = await svc.get_summary(org_id=current_user.org_id)

    return DashboardSummaryResponse(
        total_assets=data["total_assets"],
        total_vulnerabilities=data["total_vulnerabilities"],
        open_vulnerabilities=data["open_vulnerabilities"],
        critical_count=data["critical_count"],
        high_count=data["high_count"],
        medium_count=data["medium_count"],
        low_count=data["low_count"],
        recent_scans=[ScanJobResponse.model_validate(s) for s in data["recent_scans"]],
    )


@router.get(
    "/health-score", response_model=HealthScoreResponse, summary="Security health score"
)
async def get_health_score(current_user: CurrentUser, db: DBSession) -> HealthScoreResponse:
    """Returns current security health score (0–100) with a 7-day trend."""
    svc = DashboardService(db)
    data = await svc.get_health_score(org_id=current_user.org_id)
    return HealthScoreResponse(**data)
