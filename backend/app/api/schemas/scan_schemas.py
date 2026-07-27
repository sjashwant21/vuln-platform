from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanJobCreate(BaseModel):
    """Payload for launching a new scan."""

    target_ips: list[str] = Field(..., min_length=1, description="List of IPs or subnets to scan")
    scan_type: str = Field(default="discovery", description="Type of scan (discovery, full, quick)")
    scan_options: dict[str, Any] = Field(
        default_factory=dict, description="Additional scanner options"
    )


class ScanFindingResponse(BaseModel):
    id: str
    asset_id: str
    port: int | None = None
    protocol: str | None = None
    severity: str
    title: str
    description: str
    evidence: str | None = None
    cve_ids: list[str] = Field(default_factory=list)
    cvss_score: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanJobResponse(BaseModel):
    id: str
    organization_id: str
    initiated_by_id: str | None = None
    scan_type: str
    status: str
    target_ips: list[str]
    scan_options: dict[str, Any]
    result_summary: dict[str, Any]
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    findings: list[ScanFindingResponse] | None = None

    model_config = ConfigDict(from_attributes=True)
