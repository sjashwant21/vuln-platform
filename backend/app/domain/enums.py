"""
Domain enumerations.

Pure Python — no framework imports. These are the core business vocabulary.
str mixin ensures values serialize cleanly to JSON and PostgreSQL VARCHAR columns.
"""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    """RBAC roles scoped to an organization."""
    OWNER   = "owner"    # Full access + billing + delete org
    ADMIN   = "admin"    # Full access except billing
    ANALYST = "analyst"  # Read/write scans, vulns, reports
    VIEWER  = "viewer"   # Read-only

    def can_write(self) -> bool:
        return self in (UserRole.OWNER, UserRole.ADMIN, UserRole.ANALYST)

    def is_admin_or_above(self) -> bool:
        return self in (UserRole.OWNER, UserRole.ADMIN)

    def is_owner(self) -> bool:
        return self == UserRole.OWNER


class PlanTier(str, enum.Enum):
    FREE         = "free"
    STARTER      = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE   = "enterprise"

    @property
    def max_assets(self) -> int:
        limits = {
            PlanTier.FREE: 5,
            PlanTier.STARTER: 50,
            PlanTier.PROFESSIONAL: 500,
            PlanTier.ENTERPRISE: 99999,
        }
        return limits[self]

    @property
    def max_users(self) -> int:
        limits = {
            PlanTier.FREE: 2,
            PlanTier.STARTER: 10,
            PlanTier.PROFESSIONAL: 50,
            PlanTier.ENTERPRISE: 99999,
        }
        return limits[self]

    @property
    def max_concurrent_scans(self) -> int:
        limits = {
            PlanTier.FREE: 1,
            PlanTier.STARTER: 3,
            PlanTier.PROFESSIONAL: 10,
            PlanTier.ENTERPRISE: 50,
        }
        return limits[self]


class AssetType(str, enum.Enum):
    SERVER         = "server"
    WORKSTATION    = "workstation"
    NETWORK_DEVICE = "network_device"
    IOT            = "iot"
    CLOUD_INSTANCE = "cloud_instance"
    CONTAINER      = "container"
    UNKNOWN        = "unknown"


class AssetCriticality(str, enum.Enum):
    CRITICAL = "critical"   # Tier 1 — prod / public facing
    HIGH     = "high"       # Tier 2 — internal prod
    MEDIUM   = "medium"     # Tier 3 — internal non-prod
    LOW      = "low"        # Tier 4 — dev/test/lab

    @property
    def risk_multiplier(self) -> float:
        """Used to adjust CVSS-based risk scoring per asset criticality."""
        multipliers = {
            AssetCriticality.CRITICAL: 1.5,
            AssetCriticality.HIGH: 1.2,
            AssetCriticality.MEDIUM: 1.0,
            AssetCriticality.LOW: 0.7,
        }
        return multipliers[self]


class ScanType(str, enum.Enum):
    DISCOVERY      = "discovery"       # Ping sweep — find live hosts
    PORT_SCAN      = "port_scan"       # TCP/UDP port enumeration
    SERVICE_ENUM   = "service_enum"    # Service + version detection
    VULNERABILITY  = "vulnerability"   # Full assessment (all of above)
    CVE_CORRELATION = "cve_correlation" # Re-correlate existing findings


class ScanStatus(str, enum.Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"

    def is_terminal(self) -> bool:
        return self in (
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
            ScanStatus.TIMEOUT,
        )

    def is_cancellable(self) -> bool:
        return self in (ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING)


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"   # CVSS 9.0–10.0
    HIGH     = "high"       # CVSS 7.0–8.9
    MEDIUM   = "medium"     # CVSS 4.0–6.9
    LOW      = "low"        # CVSS 0.1–3.9
    INFO     = "info"       # CVSS 0.0 / informational

    @property
    def score_weight(self) -> int:
        """Used in health score deduction formula."""
        return {
            SeverityLevel.CRITICAL: 20,
            SeverityLevel.HIGH: 8,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 1,
            SeverityLevel.INFO: 0,
        }[self]

    @classmethod
    def from_cvss(cls, score: float) -> SeverityLevel:
        if score >= 9.0:
            return cls.CRITICAL
        if score >= 7.0:
            return cls.HIGH
        if score >= 4.0:
            return cls.MEDIUM
        if score > 0.0:
            return cls.LOW
        return cls.INFO


class VulnerabilityStatus(str, enum.Enum):
    OPEN          = "open"
    IN_PROGRESS   = "in_progress"
    RESOLVED      = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"


class AuditAction(str, enum.Enum):
    # Auth
    LOGIN          = "auth.login"
    LOGOUT         = "auth.logout"
    LOGIN_FAILED   = "auth.login_failed"
    TOKEN_REFRESH  = "auth.token_refresh"
    MFA_ENABLED    = "auth.mfa_enabled"
    MFA_DISABLED   = "auth.mfa_disabled"
    PASSWORD_CHANGED = "auth.password_changed"
    # Users
    USER_CREATED   = "user.created"
    USER_UPDATED   = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    ROLE_CHANGED   = "user.role_changed"
    # Organization
    ORG_CREATED    = "org.created"
    ORG_UPDATED    = "org.updated"
    MEMBER_INVITED = "org.member_invited"
    MEMBER_REMOVED = "org.member_removed"
    # Assets
    ASSET_CREATED  = "asset.created"
    ASSET_UPDATED  = "asset.updated"
    ASSET_DELETED  = "asset.deleted"
    # Scans
    SCAN_STARTED   = "scan.started"
    SCAN_COMPLETED = "scan.completed"
    SCAN_CANCELLED = "scan.cancelled"
    SCAN_FAILED    = "scan.failed"
    # Vulnerabilities
    VULN_STATUS_CHANGED  = "vuln.status_changed"
    VULN_FALSE_POSITIVE  = "vuln.false_positive"
    # Reports
    REPORT_GENERATED = "report.generated"
    REPORT_DOWNLOADED = "report.downloaded"
