"""
SQLAlchemy 2.0 ORM models (infrastructure layer).

Design decisions:
  - UUID primary keys (str) — portable, no auto-increment race conditions
  - organization_id on every tenant-scoped table — enforced at DB level
  - JSONB for flexible metadata — avoids schema migrations for minor additions
  - Soft deletes via is_active flag — preserves audit history
  - server_default for timestamps — DB-side precision, immune to app clock skew
  - No lazy loading — explicit selectinload() everywhere to prevent N+1
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Shared base with JSONB type map."""

    type_annotation_map = {dict[str, Any]: JSONB}


# ══════════════════════════════════════════════════════════════════
# Organization & Users
# ══════════════════════════════════════════════════════════════════

class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[str]   = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63),  nullable=False, unique=True, index=True)

    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    max_assets: Mapped[int]          = mapped_column(Integer, nullable=False, default=5)
    max_users: Mapped[int]           = mapped_column(Integer, nullable=False, default=2)
    max_concurrent_scans: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(
        "UserModel", back_populates="organization", lazy="noload"
    )


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_org_email", "organization_id", "email"),
        Index("ix_users_org_active", "organization_id", "is_active"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str]        = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str]    = mapped_column(String(255), nullable=False)
    role: Mapped[str]         = mapped_column(String(50),  nullable=False, default="viewer")

    mfa_secret: Mapped[str | None]  = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool]         = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool]    = mapped_column(Boolean, nullable=False, default=False)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", back_populates="users", lazy="noload"
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel", back_populates="user",
        cascade="all, delete-orphan", lazy="noload"
    )


class RefreshTokenModel(Base):
    """
    Refresh token store — only the SHA-256 hash is persisted.
    Raw tokens exist only in memory during generation and are sent to the
    client once. A DB breach cannot yield usable tokens.
    """
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id",   "user_id"),
        Index("ix_refresh_tokens_token_hash", "token_hash"),
    )

    id: Mapped[str]         = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str]    = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool]        = mapped_column(Boolean, nullable=False, default=False)

    ip_address: Mapped[str | None] = mapped_column(String(45),  nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="refresh_tokens", lazy="noload"
    )


# ══════════════════════════════════════════════════════════════════
# Assets
# ══════════════════════════════════════════════════════════════════

class AssetModel(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "ip_address", name="uq_assets_org_ip"),
        Index("ix_assets_org_active",    "organization_id", "is_active"),
        Index("ix_assets_ip",            "ip_address"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    hostname: Mapped[str | None]    = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str]         = mapped_column(String(45),  nullable=False)
    asset_type: Mapped[str]         = mapped_column(String(50),  nullable=False, default="unknown")
    os_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str]        = mapped_column(String(20),  nullable=False, default="medium")
    tags: Mapped[dict[str, Any]]          = mapped_column(JSONB, nullable=False, default=dict)
    asset_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    is_active: Mapped[bool]              = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]         = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    ports: Mapped[list["AssetPortModel"]] = relationship(
        "AssetPortModel", back_populates="asset",
        cascade="all, delete-orphan", lazy="noload"
    )
    vulnerabilities: Mapped[list["VulnerabilityModel"]] = relationship(
        "VulnerabilityModel", back_populates="asset", lazy="noload"
    )


class AssetPortModel(Base):
    __tablename__ = "asset_ports"
    __table_args__ = (
        UniqueConstraint("asset_id", "port", "protocol", name="uq_port_asset_port_proto"),
        Index("ix_asset_ports_asset_id", "asset_id"),
    )

    id: Mapped[str]       = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    port: Mapped[int]             = mapped_column(Integer, nullable=False)
    protocol: Mapped[str]         = mapped_column(String(10), nullable=False, default="tcp")
    service: Mapped[str | None]         = mapped_column(String(100), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner: Mapped[str | None]          = mapped_column(Text, nullable=True)
    state: Mapped[str]            = mapped_column(String(20), nullable=False, default="open")
    scanned_at: Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset: Mapped["AssetModel"] = relationship(
        "AssetModel", back_populates="ports", lazy="noload"
    )


# ══════════════════════════════════════════════════════════════════
# Scans
# ══════════════════════════════════════════════════════════════════

class ScanJobModel(Base):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        Index("ix_scan_jobs_org_status", "organization_id", "status"),
        Index("ix_scan_jobs_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    initiated_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    scan_type: Mapped[str]  = mapped_column(String(50), nullable=False)
    status: Mapped[str]     = mapped_column(String(30), nullable=False, default="pending")
    target_ips: Mapped[list[str]] = mapped_column(
        ARRAY(String(45)), nullable=False, default=list
    )
    scan_options: Mapped[dict[str, Any]]  = mapped_column(JSONB, nullable=False, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None]      = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]          = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    findings: Mapped[list["ScanFindingModel"]] = relationship(
        "ScanFindingModel", back_populates="scan_job",
        cascade="all, delete-orphan", lazy="noload"
    )


class ScanFindingModel(Base):
    __tablename__ = "scan_findings"
    __table_args__ = (
        Index("ix_scan_findings_job_id",   "scan_job_id"),
        Index("ix_scan_findings_asset_id", "asset_id"),
        Index("ix_scan_findings_severity", "severity"),
    )

    id: Mapped[str]         = mapped_column(String(36), primary_key=True, default=_uuid)
    scan_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    port: Mapped[int | None]     = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    severity: Mapped[str]        = mapped_column(String(20), nullable=False, default="info")
    title: Mapped[str]           = mapped_column(String(500), nullable=False)
    description: Mapped[str]     = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    cve_ids: Mapped[list[str]]   = mapped_column(
        ARRAY(String(20)), nullable=False, default=list
    )
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scan_job: Mapped["ScanJobModel"] = relationship(
        "ScanJobModel", back_populates="findings", lazy="noload"
    )


# ══════════════════════════════════════════════════════════════════
# CVE cache & Vulnerabilities
# ══════════════════════════════════════════════════════════════════

class CVECacheModel(Base):
    __tablename__ = "cve_cache"

    id: Mapped[str]     = mapped_column(String(36), primary_key=True, default=_uuid)
    cve_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    description: Mapped[str]           = mapped_column(Text, nullable=False)
    cvss_v3_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    cvss_v3_vector: Mapped[str | None]  = mapped_column(String(255), nullable=True)
    severity: Mapped[str]               = mapped_column(String(20), nullable=False, default="unknown")
    affected_products: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    references: Mapped[dict[str, Any]]        = mapped_column(JSONB, nullable=False, default=list)
    cwe_ids: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime]           = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VulnerabilityModel(Base):
    __tablename__ = "vulnerabilities"
    __table_args__ = (
        Index("ix_vulns_org_status",   "organization_id", "status"),
        Index("ix_vulns_org_severity", "organization_id", "severity"),
        Index("ix_vulns_asset_id",     "asset_id"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scan_findings.id", ondelete="SET NULL"), nullable=True
    )
    cve_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cve_cache.cve_id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str]       = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str]    = mapped_column(String(20), nullable=False)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str]      = mapped_column(String(30), nullable=False, default="open")
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None]   = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime]          = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime]           = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped["AssetModel"] = relationship(
        "AssetModel", back_populates="vulnerabilities", lazy="noload"
    )
    remediation_plans: Mapped[list["RemediationPlanModel"]] = relationship(
        "RemediationPlanModel", back_populates="vulnerability",
        cascade="all, delete-orphan", lazy="noload"
    )


class RemediationPlanModel(Base):
    __tablename__ = "remediation_plans"
    __table_args__ = (
        Index("ix_remediation_vuln_id", "vulnerability_id"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    vulnerability_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False
    )
    ai_model: Mapped[str]               = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int]          = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int]      = mapped_column(Integer, nullable=False, default=0)
    recommendation_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_steps: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_score: Mapped[float | None]   = mapped_column(Float, nullable=True)
    accepted: Mapped[bool]               = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime]       = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vulnerability: Mapped["VulnerabilityModel"] = relationship(
        "VulnerabilityModel", back_populates="remediation_plans", lazy="noload"
    )


# ══════════════════════════════════════════════════════════════════
# Reports
# ══════════════════════════════════════════════════════════════════

class ReportModel(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_org_id", "organization_id"),
    )

    id: Mapped[str]              = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    scan_job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scan_jobs.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str]       = mapped_column(String(500), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50),  nullable=False)
    format: Mapped[str]      = mapped_column(String(10),  nullable=False, default="pdf")
    health_score: Mapped[int | None]      = mapped_column(Integer, nullable=True)
    total_assets: Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    total_vulnerabilities: Mapped[int]    = mapped_column(Integer, nullable=False, default=0)
    critical_count: Mapped[int]           = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int]               = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int]                = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str | None]      = mapped_column(String(1000), nullable=True)
    generation_status: Mapped[str]        = mapped_column(String(20), nullable=False, default="pending")
    generated_at: Mapped[datetime]        = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ══════════════════════════════════════════════════════════════════
# Audit log (append-only)
# ══════════════════════════════════════════════════════════════════

class AuditLogModel(Base):
    """
    Immutable audit trail. Application code MUST NOT issue UPDATE or DELETE
    against this table. The service layer enforces append-only via the
    AuditLogger helper which only calls repository.append().
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_created",  "organization_id", "created_at"),
        Index("ix_audit_user_id",      "user_id"),
        Index("ix_audit_action",       "action"),
        Index("ix_audit_resource",     "resource_type", "resource_id"),
    )

    id: Mapped[str]                    = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str | None]         = mapped_column(String(36), nullable=True)
    action: Mapped[str]                 = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None]   = mapped_column(String(50),  nullable=True)
    resource_id: Mapped[str | None]     = mapped_column(String(36),  nullable=True)
    ip_address: Mapped[str | None]      = mapped_column(String(45),  nullable=True)
    user_agent: Mapped[str | None]      = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None]      = mapped_column(String(36),  nullable=True)
    payload: Mapped[dict[str, Any]]     = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime]        = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
