"""
Pydantic v2 request/response schemas for the vulnerability intelligence API.

Schema design:
  - Request schemas are strict — bad input fails immediately with clear errors
  - Response schemas are lenient — missing fields become None, not errors
  - All scores are floats 0.0–10.0 with explicit range validation
  - Severity is a string enum to survive API evolution without breaking clients
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ── Request schemas ────────────────────────────────────────────

class CorrelateRequest(BaseModel):
    """Single service/version CVE correlation query."""

    service: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Software or service name (e.g. 'nginx', 'apache httpd', 'openssl')",
        examples=["nginx", "apache httpd", "openssl"],
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Version string (e.g. '1.18.0', '2.4.51', '3.0.7')",
        examples=["1.18.0", "2.4.51", "3.0.7"],
    )
    asset_criticality: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
        description="Business criticality of the asset running this service",
    )
    internet_exposed: bool = Field(
        default=False,
        description="Whether the asset is reachable from the internet",
    )
    use_live_nvd: bool = Field(
        default=True,
        description="Query NVD live (slower but more complete) vs cache-only",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum CVE matches to return",
    )

    @field_validator("service", "version", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        return v.strip()


class BatchCorrelateRequest(BaseModel):
    """Batch correlation for multiple service/version pairs."""

    targets: list[CorrelateRequest] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of service/version pairs to correlate (max 20)",
    )
    asset_criticality: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
    )
    internet_exposed: bool = Field(default=False)


class RescoreRequest(BaseModel):
    """Re-score an existing CVE with updated context."""

    cve_id:            str = Field(..., pattern=r"^CVE-\d{4}-\d{4,}$")
    asset_criticality: Literal["critical", "high", "medium", "low"] = "medium"
    internet_exposed:  bool = False
    data_sensitivity:  Literal["public", "internal", "confidential", "secret"] = "internal"


# ── Nested response schemas ────────────────────────────────────

class CVSSMetricsResponse(BaseModel):
    version:             str
    base_score:          float
    vector_string:       str
    severity:            str
    attack_vector:       str | None = None
    attack_complexity:   str | None = None
    privileges_required: str | None = None
    user_interaction:    str | None = None
    is_network_exploitable: bool = False
    requires_no_privileges: bool = False

    model_config = {"from_attributes": True}


class CVEReferenceResponse(BaseModel):
    url:       str
    tags:      list[str]
    is_patch:  bool = False
    is_exploit:bool = False

    model_config = {"from_attributes": True}


class CVEResponse(BaseModel):
    """Full CVE data returned in correlation results."""

    cve_id:           str
    description:      str
    severity:         str
    cvss_v3:          CVSSMetricsResponse | None = None
    cvss_v2:          CVSSMetricsResponse | None = None
    base_score:       float | None = None
    cwe_ids:          list[str] = Field(default_factory=list)
    references:       list[CVEReferenceResponse] = Field(default_factory=list)
    published_at:     datetime | None = None
    has_public_exploit: bool = False
    has_patch:          bool = False

    model_config = {"from_attributes": True}


class CorrelationMatchResponse(BaseModel):
    """One matched CVE within a correlation result."""

    cve_id:          str
    cve:             CVEResponse
    match_method:    str
    confidence:      float = Field(..., ge=0.0, le=1.0)
    risk_score:      float = Field(..., ge=0.0, le=10.0)
    matched_service: str
    matched_version: str
    severity:        str

    model_config = {"from_attributes": True}


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high:     int = 0
    medium:   int = 0
    low:      int = 0
    none:     int = 0
    total:    int = 0


class IntelligenceReportResponse(BaseModel):
    """Full correlation result for one (service, version) query."""

    service:           str
    version:           str
    query_time_ms:     float
    total_findings:    int
    max_cvss_score:    float | None = None
    max_risk_score:    float
    has_exploitable:   bool
    severity_breakdown:SeverityBreakdown
    matches:           list[CorrelationMatchResponse]


class BatchReportResponse(BaseModel):
    """Results of a batch correlation query."""

    total_targets:  int
    total_findings: int
    reports:        list[IntelligenceReportResponse]


class CVEDetailResponse(BaseModel):
    """Detailed single-CVE lookup response."""

    cve:              CVEResponse
    risk_score:       float | None = None
    score_factors:    dict | None  = None
    cached:           bool = False
    cache_age_hours:  float | None = None


class IngestionStatusResponse(BaseModel):
    """Status of the background CVE ingestion pipeline."""

    last_incremental_sync: datetime | None = None
    last_full_reconcile:   datetime | None = None
    total_cached_cves:     int
    stale_count:           int
    redis_token_remaining: float


# ── Conversion helpers ─────────────────────────────────────────

def report_to_response(report: object) -> IntelligenceReportResponse:
    """Convert IntelligenceReport domain object to API response schema."""
    from app.domain.models.cve import IntelligenceReport

    r: IntelligenceReport = report  # type: ignore[assignment]

    breakdown = SeverityBreakdown(
        critical=r.critical_count,
        high=    r.high_count,
        medium=  r.medium_count,
        low=     r.low_count,
        total=   r.total_findings,
    )

    matches = []
    for m in r.sorted_by_risk():
        cve = m.cve

        cvss_v3 = None
        if cve.cvss_v3:
            cvss_v3 = CVSSMetricsResponse(
                version=             cve.cvss_v3.version,
                base_score=          cve.cvss_v3.base_score,
                vector_string=       cve.cvss_v3.vector_string,
                severity=            cve.cvss_v3.severity.value,
                attack_vector=       cve.cvss_v3.attack_vector,
                attack_complexity=   cve.cvss_v3.attack_complexity,
                privileges_required= cve.cvss_v3.privileges_required,
                user_interaction=    cve.cvss_v3.user_interaction,
                is_network_exploitable=cve.cvss_v3.is_network_exploitable,
                requires_no_privileges=cve.cvss_v3.requires_no_privileges,
            )

        cvss_v2 = None
        if cve.cvss_v2:
            cvss_v2 = CVSSMetricsResponse(
                version=      cve.cvss_v2.version,
                base_score=   cve.cvss_v2.base_score,
                vector_string=cve.cvss_v2.vector_string,
                severity=     cve.cvss_v2.severity.value,
            )

        refs = [
            CVEReferenceResponse(
                url=r.url,
                tags=list(r.tags),
                is_patch=r.is_patch(),
                is_exploit=r.is_exploit(),
            )
            for r in cve.references
        ]

        cve_resp = CVEResponse(
            cve_id=           cve.cve_id,
            description=      cve.description,
            severity=         cve.severity.value,
            cvss_v3=          cvss_v3,
            cvss_v2=          cvss_v2,
            base_score=       cve.base_score,
            cwe_ids=          list(cve.cwe_ids),
            references=       refs,
            published_at=     cve.published_at,
            has_public_exploit=cve.has_public_exploit,
            has_patch=        cve.has_patch,
        )

        matches.append(CorrelationMatchResponse(
            cve_id=         m.cve_id,
            cve=            cve_resp,
            match_method=   m.match_method.value,
            confidence=     m.confidence,
            risk_score=     m.risk_score,
            matched_service=m.matched_service,
            matched_version=m.matched_version,
            severity=       m.severity.value,
        ))

    return IntelligenceReportResponse(
        service=           r.service,
        version=           r.version,
        query_time_ms=     r.query_time_ms,
        total_findings=    r.total_findings,
        max_cvss_score=    r.max_cvss_score,
        max_risk_score=    r.max_risk_score,
        has_exploitable=   r.has_exploitable_vulns,
        severity_breakdown=breakdown,
        matches=           matches,
    )
