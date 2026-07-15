"""
Pure domain models for the reporting engine.

Every concept a report needs lives here as a frozen dataclass.
No ORM, no HTTP, no rendering logic.

Design:
  ReportData is the single data contract between the assembler and
  all renderers. Adding a new renderer requires zero changes here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ReportType(str, Enum):
    EXECUTIVE    = "executive"
    TECHNICAL    = "technical"
    VULNERABILITY = "vulnerability"
    COMPLIANCE   = "compliance"


class ReportFormat(str, Enum):
    PDF  = "pdf"
    DOCX = "docx"
    HTML = "html"   # intermediate / preview


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"

    @property
    def color_hex(self) -> str:
        return {
            SeverityLevel.CRITICAL: "#DC2626",
            SeverityLevel.HIGH:     "#EA580C",
            SeverityLevel.MEDIUM:   "#D97706",
            SeverityLevel.LOW:      "#2563EB",
            SeverityLevel.INFO:     "#6B7280",
        }[self]

    @property
    def order(self) -> int:
        return {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH:     1,
            SeverityLevel.MEDIUM:   2,
            SeverityLevel.LOW:      3,
            SeverityLevel.INFO:     4,
        }[self]


# ── Asset inventory ────────────────────────────────────────────

@dataclass(frozen=True)
class AssetSummary:
    asset_id:    str
    hostname:    str | None
    ip_address:  str
    asset_type:  str
    criticality: str
    os:          str | None
    open_ports:  int
    vuln_critical: int
    vuln_high:   int
    vuln_medium: int
    vuln_low:    int
    risk_score:  float
    last_scanned: datetime | None

    @property
    def total_vulns(self) -> int:
        return self.vuln_critical + self.vuln_high + self.vuln_medium + self.vuln_low

    @property
    def display_name(self) -> str:
        return self.hostname or self.ip_address


# ── Vulnerability detail ───────────────────────────────────────

@dataclass(frozen=True)
class VulnDetail:
    vuln_id:      str
    cve_id:       str | None
    title:        str
    severity:     SeverityLevel
    cvss_score:   float | None
    asset_name:   str
    asset_ip:     str
    service:      str
    port:         int | None
    status:       str
    detected_at:  datetime
    has_exploit:  bool
    has_patch:    bool
    description:  str
    remediation:  str | None    # AI-generated recommendation if available

    @property
    def age_days(self) -> int:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        detected = self.detected_at
        if detected.tzinfo is None:
            from datetime import timezone
            detected = detected.replace(tzinfo=timezone.utc)
        return (now - detected).days


# ── Risk trend data ────────────────────────────────────────────

@dataclass(frozen=True)
class RiskTrendPoint:
    date:     datetime
    critical: int
    high:     int
    medium:   int
    low:      int
    score:    float   # health score 0-100

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low


# ── Compliance check ───────────────────────────────────────────

@dataclass(frozen=True)
class ComplianceControl:
    control_id:   str     # e.g. "PCI-DSS 6.3.3", "SOC2 CC6.1"
    framework:    str     # "PCI-DSS" | "SOC2" | "ISO27001" | "NIST"
    title:        str
    status:       str     # "compliant" | "non_compliant" | "partial" | "not_applicable"
    related_vulns: tuple[str, ...]  # CVE IDs
    finding:      str
    remediation:  str
    severity:     str


@dataclass(frozen=True)
class ComplianceSummary:
    framework:     str
    compliant:     int
    non_compliant: int
    partial:       int
    not_applicable:int
    controls:      tuple[ComplianceControl, ...]

    @property
    def total(self) -> int:
        return self.compliant + self.non_compliant + self.partial + self.not_applicable

    @property
    def compliance_pct(self) -> float:
        applicable = self.compliant + self.non_compliant + self.partial
        if applicable == 0:
            return 100.0
        return round(self.compliant / applicable * 100, 1)


# ── AI recommendation ──────────────────────────────────────────

@dataclass(frozen=True)
class AIRecommendation:
    priority:    int
    title:       str
    description: str
    effort:      str     # "immediate" | "short_term" | "long_term"
    impact:      str
    cve_refs:    tuple[str, ...]


# ── Severity distribution ──────────────────────────────────────

@dataclass(frozen=True)
class SeverityDistribution:
    critical: int
    high:     int
    medium:   int
    low:      int
    info:     int = 0

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low + self.info

    def as_dict(self) -> dict[str, int]:
        return {
            "critical": self.critical,
            "high":     self.high,
            "medium":   self.medium,
            "low":      self.low,
            "info":     self.info,
        }


# ── Master report data ─────────────────────────────────────────

@dataclass(frozen=True)
class ReportData:
    """
    Complete data payload fed to every renderer.
    Assembled once by ReportDataAssembler, consumed by PDF/DOCX renderers.
    """
    # Metadata
    report_id:      str
    report_type:    ReportType
    org_name:       str
    generated_at:   datetime
    generated_by:   str
    period_start:   datetime
    period_end:     datetime
    scan_job_id:    str | None

    # Health
    health_score:   int
    health_label:   str
    health_delta:   int | None   # change vs prior period (+/- points)

    # Distributions
    severity_distribution: SeverityDistribution

    # Assets
    total_assets:   int
    assets:         tuple[AssetSummary, ...]

    # Vulnerabilities
    total_vulns:    int
    open_vulns:     int
    resolved_vulns: int
    accepted_risk:  int
    vulns:          tuple[VulnDetail, ...]

    # Trends
    risk_trend:     tuple[RiskTrendPoint, ...]

    # Compliance (empty tuple for non-compliance reports)
    compliance:     tuple[ComplianceSummary, ...]

    # AI content
    executive_summary:    str
    ai_recommendations:   tuple[AIRecommendation, ...]
    management_summary:   str | None

    # Report-type-specific extras
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_assets(self) -> tuple[AssetSummary, ...]:
        return tuple(a for a in self.assets if a.criticality == "critical")

    @property
    def top_vulns_by_risk(self) -> tuple[VulnDetail, ...]:
        return tuple(sorted(
            (v for v in self.vulns if v.status == "open"),
            key=lambda v: v.cvss_score or 0,
            reverse=True,
        )[:20])

    @property
    def exploitable_open_vulns(self) -> tuple[VulnDetail, ...]:
        return tuple(
            v for v in self.vulns
            if v.status == "open" and v.has_exploit
        )
