from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScanJobCreate(BaseModel):
    """Payload for launching a new scan."""

    target_ips: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of public IP addresses or /24 CIDR blocks to scan",
    )
    scan_type: str = Field(default="discovery", description="Type of scan (discovery, full, quick)")
    scan_options: dict[str, Any] = Field(
        default_factory=dict, description="Additional scanner options"
    )

    @field_validator("target_ips", mode="before")
    @classmethod
    def validate_and_sanitize_ips(cls, v: list[str]) -> list[str]:
        """
        Strict allowlist validation — blocks private IPs, cloud metadata
        endpoints (SSRF), oversized subnets (DoS), and hostnames.
        """
        from app.infrastructure.security.ip_validator import validate_scan_targets

        return validate_scan_targets([str(t) for t in v])

    @field_validator("scan_type")
    @classmethod
    def validate_scan_type(cls, v: str) -> str:
        allowed = {"discovery", "full", "quick", "vuln"}
        if v not in allowed:
            raise ValueError(f"scan_type must be one of: {', '.join(sorted(allowed))}")
        return v


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
