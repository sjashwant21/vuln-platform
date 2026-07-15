"""
Abstract repository interfaces (ports).
The application layer depends on these abstractions, not concrete implementations.
This enables testing with mock repositories and swapping storage backends.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.enums import ScanStatus, VulnerabilityStatus


class UserRepository(ABC):
    """Port for user persistence operations."""

    @abstractmethod
    async def get_by_id(self, user_id: str, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update(self, user_id: str, org_id: str, data: dict[str, Any]) -> Any | None:
        ...

    @abstractmethod
    async def list_by_org(self, org_id: str, limit: int, offset: int) -> list[Any]:
        ...


class OrganizationRepository(ABC):
    """Port for organization persistence operations."""

    @abstractmethod
    async def get_by_id(self, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Any | None:
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update(self, org_id: str, data: dict[str, Any]) -> Any | None:
        ...


class AssetRepository(ABC):
    """Port for asset persistence operations."""

    @abstractmethod
    async def get_by_id(self, asset_id: str, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def get_by_ip(self, ip_address: str, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def list_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Any], int]:
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update(self, asset_id: str, org_id: str, data: dict[str, Any]) -> Any | None:
        ...

    @abstractmethod
    async def delete(self, asset_id: str, org_id: str) -> bool:
        ...

    @abstractmethod
    async def upsert_port(self, asset_id: str, port_data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def count_by_org(self, org_id: str) -> int:
        ...


class ScanRepository(ABC):
    """Port for scan job persistence operations."""

    @abstractmethod
    async def get_job_by_id(self, job_id: str, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def list_jobs_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        status: ScanStatus | None = None,
    ) -> tuple[list[Any], int]:
        ...

    @abstractmethod
    async def create_job(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update_job_status(
        self,
        job_id: str,
        status: ScanStatus,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        ...

    @abstractmethod
    async def count_running_jobs(self, org_id: str) -> int:
        ...

    @abstractmethod
    async def create_finding(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def list_findings_by_job(self, job_id: str, org_id: str) -> list[Any]:
        ...


class VulnerabilityRepository(ABC):
    """Port for vulnerability persistence operations."""

    @abstractmethod
    async def get_by_id(self, vuln_id: str, org_id: str) -> Any | None:
        ...

    @abstractmethod
    async def list_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Any], int]:
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update_status(
        self,
        vuln_id: str,
        org_id: str,
        status: VulnerabilityStatus,
        reason: str | None,
        resolved_at: datetime | None,
    ) -> Any | None:
        ...

    @abstractmethod
    async def get_severity_counts(self, org_id: str) -> dict[str, int]:
        ...

    @abstractmethod
    async def create_remediation_plan(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def get_latest_remediation(self, vuln_id: str, org_id: str) -> Any | None:
        ...


class AuditLogRepository(ABC):
    """Port for audit log persistence (append-only)."""

    @abstractmethod
    async def append(self, data: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def list_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        ...


class CVECacheRepository(ABC):
    """Port for CVE data cache operations."""

    @abstractmethod
    async def get_by_cve_id(self, cve_id: str) -> Any | None:
        ...

    @abstractmethod
    async def upsert(self, data: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def bulk_upsert(self, records: list[dict[str, Any]]) -> int:
        ...

    @abstractmethod
    async def get_by_cve_ids(self, cve_ids: list[str]) -> list[Any]:
        ...
