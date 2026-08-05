"""Vulnerabilities API router — /v1/vulnerabilities/*"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.vulnerability_schemas import (
    RemediationPlanResponse,
    VulnerabilityResponse,
    VulnListResponse,
    VulnStatusUpdateRequest,
)
from app.application.services.vulnerability_service import VulnerabilityService
from app.dependencies import CurrentUser, get_db_session
from app.domain.exceptions import ResourceNotFoundError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/vulnerabilities", tags=["Vulnerabilities"])

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


def _svc(db: DBSession) -> VulnerabilityService:
    return VulnerabilityService(db)


@router.get("", response_model=VulnListResponse, summary="List vulnerabilities")
async def list_vulnerabilities(
    current_user: CurrentUser,
    db: DBSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None, alias="status"),
    asset_id: str | None = Query(default=None),
) -> VulnListResponse:
    """List vulnerabilities for the current org, with optional filters."""
    items, total = await _svc(db).list_vulnerabilities(
        org_id=current_user.org_id,
        limit=limit,
        offset=offset,
        severity=severity,
        status=status,
        asset_id=asset_id,
    )
    return VulnListResponse(
        items=[VulnerabilityResponse.model_validate(v) for v in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{vuln_id}", response_model=VulnerabilityResponse, summary="Get vulnerability")
async def get_vulnerability(
    vuln_id: str, current_user: CurrentUser, db: DBSession
) -> VulnerabilityResponse:
    try:
        vuln = await _svc(db).get_vulnerability(org_id=current_user.org_id, vuln_id=vuln_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return VulnerabilityResponse.model_validate(vuln)


@router.patch("/{vuln_id}/status", response_model=VulnerabilityResponse, summary="Update status")
async def update_status(
    vuln_id: str,
    body: VulnStatusUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> VulnerabilityResponse:
    try:
        vuln = await _svc(db).update_status(
            org_id=current_user.org_id, vuln_id=vuln_id, data=body
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return VulnerabilityResponse.model_validate(vuln)


@router.get(
    "/{vuln_id}/remediation",
    response_model=RemediationPlanResponse,
    summary="Get remediation plan",
)
async def get_remediation(
    vuln_id: str, current_user: CurrentUser, db: DBSession
) -> RemediationPlanResponse:
    """Fetch the latest AI-generated remediation plan for a vulnerability."""
    from sqlalchemy import and_, select

    from app.infrastructure.database.models import RemediationPlanModel, VulnerabilityModel

    # Verify vuln belongs to org
    vuln_stmt = select(VulnerabilityModel).where(
        and_(VulnerabilityModel.id == vuln_id, VulnerabilityModel.organization_id == current_user.org_id)
    )
    vuln = (await db.execute(vuln_stmt)).scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vuln_id} not found")

    plan_stmt = (
        select(RemediationPlanModel)
        .where(RemediationPlanModel.vulnerability_id == vuln_id)
        .order_by(RemediationPlanModel.generated_at.desc())
        .limit(1)
    )
    plan = (await db.execute(plan_stmt)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No remediation plan found for this vulnerability")

    return RemediationPlanResponse.model_validate(plan)


@router.post(
    "/{vuln_id}/remediation",
    response_model=RemediationPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI remediation plan",
)
async def generate_remediation(
    vuln_id: str, current_user: CurrentUser, db: DBSession
) -> RemediationPlanResponse:
    """Generate a new AI remediation plan. Requires GROQ_API_KEY to be configured."""
    from sqlalchemy import and_, select

    from app.infrastructure.database.models import VulnerabilityModel

    # Verify vuln belongs to org
    vuln_stmt = (
        select(VulnerabilityModel)
        .where(and_(VulnerabilityModel.id == vuln_id, VulnerabilityModel.organization_id == current_user.org_id))
    )
    vuln = (await db.execute(vuln_stmt)).scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vuln_id} not found")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI remediation generation requires a configured LLM provider. Use the AI Analysis endpoint.",
    )
