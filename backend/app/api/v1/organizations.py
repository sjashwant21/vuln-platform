"""
Organization router — /v1/organizations/*

Tenants only see their own organization.
There is no cross-org listing endpoint exposed to tenant users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas.user_schemas import OrgResponse, UpdateOrgRequest
from app.dependencies import CurrentUser, OrgSvc, require_role
from app.domain.enums import UserRole

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ── GET /organizations/me ──────────────────────────────────────

@router.get(
    "/me",
    response_model=OrgResponse,
    summary="Get current organisation details",
)
async def get_my_org(
    current_user: CurrentUser,
    service:      OrgSvc,
) -> OrgResponse:
    dto = await service.get_org(current_user.org_id)
    return OrgResponse(
        id=dto.id,
        name=dto.name,
        slug=dto.slug,
        plan_tier=dto.plan_tier,
        max_assets=dto.max_assets,
        max_users=dto.max_users,
        max_concurrent_scans=dto.max_concurrent_scans,
        is_active=dto.is_active,
        created_at=dto.created_at,
    )


# ── PATCH /organizations/me ────────────────────────────────────

@router.patch(
    "/me",
    response_model=OrgResponse,
    summary="Update organisation details (admin+)",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OWNER))],
)
async def update_my_org(
    body:         UpdateOrgRequest,
    current_user: CurrentUser,
    service:      OrgSvc,
) -> OrgResponse:
    dto = await service.update_org(
        org_id=current_user.org_id,
        acting_role=UserRole(current_user.role),
        acting_user_id=current_user.user_id,
        name=body.name,
        settings=body.settings,
    )
    return OrgResponse(
        id=dto.id,
        name=dto.name,
        slug=dto.slug,
        plan_tier=dto.plan_tier,
        max_assets=dto.max_assets,
        max_users=dto.max_users,
        max_concurrent_scans=dto.max_concurrent_scans,
        is_active=dto.is_active,
        created_at=dto.created_at,
    )
