"""
Scan job and findings repository.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.interfaces.repositories import ScanRepository
from app.domain.enums import ScanStatus
from app.infrastructure.database.models import ScanFindingModel, ScanJobModel


class SQLScanRepository(ScanRepository):
    """Async SQLAlchemy implementation of ScanRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_job_by_id(self, job_id: str, org_id: str) -> ScanJobModel | None:
        stmt = (
            select(ScanJobModel)
            .where(
                and_(
                    ScanJobModel.id == job_id,
                    ScanJobModel.organization_id == org_id,
                )
            )
            .options(selectinload(ScanJobModel.findings))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        status: ScanStatus | None = None,
    ) -> tuple[list[ScanJobModel], int]:
        conditions: list[Any] = [ScanJobModel.organization_id == org_id]
        if status:
            conditions.append(ScanJobModel.status == status.value)

        count_stmt = (
            select(func.count())
            .select_from(ScanJobModel)
            .where(and_(*conditions))
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        data_stmt = (
            select(ScanJobModel)
            .where(and_(*conditions))
            .order_by(ScanJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def create_job(self, data: dict[str, Any]) -> ScanJobModel:
        job = ScanJobModel(id=str(uuid.uuid4()), **data)
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def update_job_status(
        self,
        job_id: str,
        status: ScanStatus,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        update_values: dict[str, Any] = {"status": status.value}

        if status == ScanStatus.RUNNING:
            update_values["started_at"] = datetime.now(UTC)
        elif status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED, ScanStatus.TIMEOUT):
            update_values["completed_at"] = datetime.now(UTC)

        if extra_data:
            update_values.update(extra_data)

        stmt = (
            update(ScanJobModel)
            .where(ScanJobModel.id == job_id)
            .values(**update_values)
        )
        await self._session.execute(stmt)

    async def count_running_jobs(self, org_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(ScanJobModel)
            .where(
                and_(
                    ScanJobModel.organization_id == org_id,
                    ScanJobModel.status.in_([ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]),
                )
            )
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def create_finding(self, data: dict[str, Any]) -> ScanFindingModel:
        finding = ScanFindingModel(id=str(uuid.uuid4()), **data)
        self._session.add(finding)
        await self._session.flush()
        return finding

    async def list_findings_by_job(
        self, job_id: str, org_id: str
    ) -> list[ScanFindingModel]:
        # Verify org ownership via join
        stmt = (
            select(ScanFindingModel)
            .join(ScanJobModel, ScanFindingModel.scan_job_id == ScanJobModel.id)
            .where(
                and_(
                    ScanFindingModel.scan_job_id == job_id,
                    ScanJobModel.organization_id == org_id,
                )
            )
            .order_by(ScanFindingModel.cvss_score.desc().nullslast())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
