"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organizations ──────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id",                   sa.String(36),  nullable=False),
        sa.Column("name",                 sa.String(255), nullable=False),
        sa.Column("slug",                 sa.String(63),  nullable=False),
        sa.Column("plan_tier",            sa.String(50),  nullable=False, server_default="free"),
        sa.Column("max_assets",           sa.Integer(),   nullable=False, server_default="5"),
        sa.Column("max_users",            sa.Integer(),   nullable=False, server_default="2"),
        sa.Column("max_concurrent_scans", sa.Integer(),   nullable=False, server_default="1"),
        sa.Column("settings",             postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active",            sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # ── users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.String(36),  nullable=False),
        sa.Column("organization_id", sa.String(36),  nullable=False),
        sa.Column("email",           sa.String(255), nullable=False),
        sa.Column("password_hash",   sa.String(255), nullable=False),
        sa.Column("full_name",       sa.String(255), nullable=False),
        sa.Column("role",            sa.String(50),  nullable=False, server_default="viewer"),
        sa.Column("mfa_secret",      sa.String(255), nullable=True),
        sa.Column("mfa_enabled",     sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("is_active",       sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("email_verified",  sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("last_login_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_org_email",  "users", ["organization_id", "email"])
    op.create_index("ix_users_org_active", "users", ["organization_id", "is_active"])

    # ── refresh_tokens ─────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id",          sa.String(36),  nullable=False),
        sa.Column("user_id",     sa.String(36),  nullable=False),
        sa.Column("token_hash",  sa.String(64),  nullable=False),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked",     sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("ip_address",  sa.String(45),  nullable=True),
        sa.Column("user_agent",  sa.String(512), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id",   "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # ── assets ─────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id",              sa.String(36),  nullable=False),
        sa.Column("organization_id", sa.String(36),  nullable=False),
        sa.Column("hostname",        sa.String(255), nullable=True),
        sa.Column("ip_address",      sa.String(45),  nullable=False),
        sa.Column("asset_type",      sa.String(50),  nullable=False, server_default="unknown"),
        sa.Column("os_fingerprint",  sa.String(255), nullable=True),
        sa.Column("criticality",     sa.String(20),  nullable=False, server_default="medium"),
        sa.Column("tags",            postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata",        postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active",       sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("last_seen_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "ip_address", name="uq_assets_org_ip"),
    )
    op.create_index("ix_assets_org_active", "assets", ["organization_id", "is_active"])
    op.create_index("ix_assets_ip",         "assets", ["ip_address"])

    # ── asset_ports ────────────────────────────────────────────
    op.create_table(
        "asset_ports",
        sa.Column("id",              sa.String(36),  nullable=False),
        sa.Column("asset_id",        sa.String(36),  nullable=False),
        sa.Column("port",            sa.Integer(),   nullable=False),
        sa.Column("protocol",        sa.String(10),  nullable=False, server_default="tcp"),
        sa.Column("service",         sa.String(100), nullable=True),
        sa.Column("service_version", sa.String(255), nullable=True),
        sa.Column("banner",          sa.Text(),      nullable=True),
        sa.Column("state",           sa.String(20),  nullable=False, server_default="open"),
        sa.Column("scanned_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "port", "protocol", name="uq_port_asset_port_proto"),
    )
    op.create_index("ix_asset_ports_asset_id", "asset_ports", ["asset_id"])

    # ── scan_jobs ──────────────────────────────────────────────
    op.create_table(
        "scan_jobs",
        sa.Column("id",               sa.String(36),  nullable=False),
        sa.Column("organization_id",  sa.String(36),  nullable=False),
        sa.Column("initiated_by_id",  sa.String(36),  nullable=True),
        sa.Column("celery_task_id",   sa.String(255), nullable=True),
        sa.Column("scan_type",        sa.String(50),  nullable=False),
        sa.Column("status",           sa.String(30),  nullable=False, server_default="pending"),
        sa.Column("target_ips",       postgresql.ARRAY(sa.String(45)), nullable=False, server_default="{}"),
        sa.Column("scan_options",     postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result_summary",   postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message",    sa.Text(),      nullable=True),
        sa.Column("started_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_jobs_org_status",  "scan_jobs", ["organization_id", "status"])
    op.create_index("ix_scan_jobs_org_created", "scan_jobs", ["organization_id", "created_at"])

    # ── scan_findings ──────────────────────────────────────────
    op.create_table(
        "scan_findings",
        sa.Column("id",          sa.String(36),  nullable=False),
        sa.Column("scan_job_id", sa.String(36),  nullable=False),
        sa.Column("asset_id",    sa.String(36),  nullable=False),
        sa.Column("port",        sa.Integer(),   nullable=True),
        sa.Column("protocol",    sa.String(10),  nullable=True),
        sa.Column("severity",    sa.String(20),  nullable=False, server_default="info"),
        sa.Column("title",       sa.String(500), nullable=False),
        sa.Column("description", sa.Text(),      nullable=False),
        sa.Column("evidence",    sa.Text(),      nullable=True),
        sa.Column("cve_ids",     postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("cvss_score",  sa.Float(),     nullable=True),
        sa.Column("raw_output",  postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"],    ["assets.id"],    ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_findings_job_id",   "scan_findings", ["scan_job_id"])
    op.create_index("ix_scan_findings_asset_id", "scan_findings", ["asset_id"])
    op.create_index("ix_scan_findings_severity", "scan_findings", ["severity"])

    # ── cve_cache ──────────────────────────────────────────────
    op.create_table(
        "cve_cache",
        sa.Column("id",               sa.String(36),  nullable=False),
        sa.Column("cve_id",           sa.String(20),  nullable=False),
        sa.Column("description",      sa.Text(),      nullable=False),
        sa.Column("cvss_v3_score",    sa.Float(),     nullable=True),
        sa.Column("cvss_v3_vector",   sa.String(255), nullable=True),
        sa.Column("severity",         sa.String(20),  nullable=False, server_default="unknown"),
        sa.Column("affected_products", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("references",       postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("cwe_ids",          postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("published_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index("ix_cve_cache_cve_id",     "cve_cache", ["cve_id"])
    op.create_index("ix_cve_cache_cvss_score", "cve_cache", ["cvss_v3_score"])

    # ── vulnerabilities ────────────────────────────────────────
    op.create_table(
        "vulnerabilities",
        sa.Column("id",              sa.String(36),  nullable=False),
        sa.Column("organization_id", sa.String(36),  nullable=False),
        sa.Column("asset_id",        sa.String(36),  nullable=False),
        sa.Column("finding_id",      sa.String(36),  nullable=True),
        sa.Column("cve_id",          sa.String(20),  nullable=True),
        sa.Column("title",           sa.String(500), nullable=False),
        sa.Column("description",     sa.Text(),      nullable=False),
        sa.Column("severity",        sa.String(20),  nullable=False),
        sa.Column("cvss_score",      sa.Float(),     nullable=True),
        sa.Column("risk_score",      sa.Float(),     nullable=True),
        sa.Column("status",          sa.String(30),  nullable=False, server_default="open"),
        sa.Column("port",            sa.Integer(),   nullable=True),
        sa.Column("service",         sa.String(100), nullable=True),
        sa.Column("notes",           sa.Text(),      nullable=True),
        sa.Column("detected_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"],        ["assets.id"],        ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"],      ["scan_findings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cve_id"],          ["cve_cache.cve_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vulns_org_status",   "vulnerabilities", ["organization_id", "status"])
    op.create_index("ix_vulns_org_severity", "vulnerabilities", ["organization_id", "severity"])
    op.create_index("ix_vulns_asset_id",     "vulnerabilities", ["asset_id"])

    # ── remediation_plans ──────────────────────────────────────
    op.create_table(
        "remediation_plans",
        sa.Column("id",                      sa.String(36),  nullable=False),
        sa.Column("organization_id",         sa.String(36),  nullable=False),
        sa.Column("vulnerability_id",        sa.String(36),  nullable=False),
        sa.Column("ai_model",                sa.String(100), nullable=False),
        sa.Column("prompt_tokens",           sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("completion_tokens",       sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("recommendation_markdown", sa.Text(),      nullable=False),
        sa.Column("structured_steps",        postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("confidence_score",        sa.Float(),     nullable=True),
        sa.Column("accepted",                sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("generated_at",            sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"],  ["organizations.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vulnerability_id"], ["vulnerabilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_remediation_vuln_id", "remediation_plans", ["vulnerability_id"])

    # ── reports ────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id",                   sa.String(36),  nullable=False),
        sa.Column("organization_id",      sa.String(36),  nullable=False),
        sa.Column("scan_job_id",          sa.String(36),  nullable=True),
        sa.Column("title",                sa.String(500), nullable=False),
        sa.Column("report_type",          sa.String(50),  nullable=False),
        sa.Column("format",               sa.String(10),  nullable=False, server_default="pdf"),
        sa.Column("health_score",         sa.Integer(),   nullable=True),
        sa.Column("total_assets",         sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("total_vulnerabilities",sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("critical_count",       sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("high_count",           sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("medium_count",         sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("low_count",            sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("storage_path",         sa.String(1000), nullable=True),
        sa.Column("generation_status",    sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("generated_at",         sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_job_id"],     ["scan_jobs.id"],     ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_org_id", "reports", ["organization_id"])

    # ── audit_logs ─────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id",              sa.String(36),  nullable=False),
        sa.Column("organization_id", sa.String(36),  nullable=True),
        sa.Column("user_id",         sa.String(36),  nullable=True),
        sa.Column("action",          sa.String(100), nullable=False),
        sa.Column("resource_type",   sa.String(50),  nullable=True),
        sa.Column("resource_id",     sa.String(36),  nullable=True),
        sa.Column("ip_address",      sa.String(45),  nullable=True),
        sa.Column("user_agent",      sa.String(512), nullable=True),
        sa.Column("request_id",      sa.String(36),  nullable=True),
        sa.Column("payload",         postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_org_created", "audit_logs", ["organization_id", "created_at"])
    op.create_index("ix_audit_user_id",     "audit_logs", ["user_id"])
    op.create_index("ix_audit_action",      "audit_logs", ["action"])
    op.create_index("ix_audit_resource",    "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reports")
    op.drop_table("remediation_plans")
    op.drop_table("vulnerabilities")
    op.drop_table("cve_cache")
    op.drop_table("scan_findings")
    op.drop_table("scan_jobs")
    op.drop_table("asset_ports")
    op.drop_table("assets")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("organizations")
