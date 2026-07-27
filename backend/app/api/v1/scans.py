from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.schemas.scan_schemas import ScanJobCreate, ScanJobResponse
from app.application.services.scan_service import ScanService
from app.dependencies import CurrentUser, get_scan_service
from app.domain.enums import ScanStatus

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post(
    "",
    response_model=ScanJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch a new vulnerability scan",
)
async def launch_scan(
    body: ScanJobCreate,
    current_user: CurrentUser,
    scan_service: Annotated[ScanService, Depends(get_scan_service)],
) -> ScanJobResponse:
    """
    Launch a new vulnerability scan against a list of target IPs.
    The job is queued to the Celery workers and executed asynchronously.
    """
    job = await scan_service.create_scan_job(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        data=body,
    )
    return ScanJobResponse.model_validate(job)


@router.get(
    "",
    response_model=list[ScanJobResponse],
    summary="List scan jobs",
)
async def list_scans(
    current_user: CurrentUser,
    scan_service: Annotated[ScanService, Depends(get_scan_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: ScanStatus | None = None,
) -> list[ScanJobResponse]:
    """List paginated scan jobs for the current organization."""
    jobs, _ = await scan_service.get_scan_jobs(
        org_id=current_user.org_id,
        limit=limit,
        offset=offset,
        status=status,
    )
    return [ScanJobResponse.model_validate(job) for job in jobs]


@router.get(
    "/{scan_id}",
    response_model=ScanJobResponse,
    summary="Get scan details",
)
async def get_scan_details(
    scan_id: str,
    current_user: CurrentUser,
    scan_service: Annotated[ScanService, Depends(get_scan_service)],
) -> ScanJobResponse:
    """Get full details of a specific scan job, including its findings."""
    job = await scan_service.get_scan_job_details(
        job_id=scan_id,
        org_id=current_user.org_id,
    )
    return ScanJobResponse.model_validate(job)
