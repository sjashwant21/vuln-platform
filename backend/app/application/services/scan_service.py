from __future__ import annotations

import structlog

from app.api.schemas.scan_schemas import ScanJobCreate
from app.application.interfaces.repositories import ScanRepository
from app.domain.enums import ScanStatus
from app.domain.exceptions import ResourceNotFoundError
from app.infrastructure.database.models import ScanJobModel

logger = structlog.get_logger(__name__)


class ScanService:
    """Service for managing vulnerability scans."""

    def __init__(self, scan_repo: ScanRepository) -> None:
        self._scan_repo = scan_repo

    async def create_scan_job(
        self,
        org_id: str,
        user_id: str,
        data: ScanJobCreate,
    ) -> ScanJobModel:
        """Create a new scan job and dispatch it to the Celery worker."""

        # 1. Persist the scan job in the database as PENDING
        job_data = {
            "organization_id": org_id,
            "initiated_by_id": user_id,
            "scan_type": data.scan_type,
            "target_ips": data.target_ips,
            "scan_options": data.scan_options,
            "status": ScanStatus.PENDING.value,
        }

        job = await self._scan_repo.create_job(job_data)
        logger.info("scan_job_created", job_id=job.id, org_id=org_id)

        # 2. Dispatch to Celery
        try:
            from app.workers.tasks.scanner import run_nmap_scan_task

            # Pass the job_id. Celery worker will fetch the details from the DB.
            task = run_nmap_scan_task.delay(job_id=job.id)

            # Update job with celery task ID
            await self._scan_repo.update_job_status(
                job_id=job.id, status=ScanStatus.QUEUED, extra_data={"celery_task_id": task.id}
            )
            logger.info("scan_job_dispatched", job_id=job.id, celery_task_id=task.id)
        except Exception as e:
            logger.error("scan_job_dispatch_failed", job_id=job.id, error=str(e))
            await self._scan_repo.update_job_status(
                job_id=job.id,
                status=ScanStatus.FAILED,
                extra_data={"error_message": f"Failed to dispatch to worker: {str(e)}"},
            )
            # We don't raise here, we return the FAILED job so the user sees it

        return job

    async def create_upload_job(
        self,
        org_id: str,
        user_id: str,
        filepath: str,
    ) -> ScanJobModel:
        """Create a new scan job for an uploaded report and dispatch it."""
        job_data = {
            "organization_id": org_id,
            "initiated_by_id": user_id,
            "scan_type": "trivy",
            "target_ips": [],
            "scan_options": {"filepath": filepath},
            "status": ScanStatus.PENDING.value,
        }

        job = await self._scan_repo.create_job(job_data)
        logger.info("upload_job_created", job_id=job.id, org_id=org_id)

        try:
            from app.workers.tasks.trivy_scanner import parse_trivy_report_task

            task = parse_trivy_report_task.delay(job_id=job.id, filepath=filepath)

            await self._scan_repo.update_job_status(
                job_id=job.id, status=ScanStatus.QUEUED, extra_data={"celery_task_id": task.id}
            )
            logger.info("upload_job_dispatched", job_id=job.id, celery_task_id=task.id)
        except Exception as e:
            logger.error("upload_job_dispatch_failed", job_id=job.id, error=str(e))
            await self._scan_repo.update_job_status(
                job_id=job.id,
                status=ScanStatus.FAILED,
                extra_data={"error_message": f"Failed to dispatch to worker: {str(e)}"},
            )

        return job

    async def get_scan_jobs(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
        status: ScanStatus | None = None,
        user_id: str | None = None,
    ) -> tuple[list[ScanJobModel], int]:
        """Get paginated scan jobs."""
        return await self._scan_repo.list_jobs_by_org(org_id, limit, offset, status, user_id)

    async def get_scan_job_details(self, job_id: str, org_id: str) -> ScanJobModel:
        """Get full details of a scan job, including findings."""
        job = await self._scan_repo.get_job_by_id(job_id, org_id)
        if not job:
            raise ResourceNotFoundError("Scan job not found.")
        return job
