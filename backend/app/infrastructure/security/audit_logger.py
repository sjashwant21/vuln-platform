"""
Structured audit logger.

Every security-relevant action is written to:
  1. audit_logs DB table (append-only, queryable)
  2. structlog JSON output (for SIEM / log aggregation)

Design: fire-and-forget from the caller's perspective.
  Audit failures MUST NOT break the primary request flow.
  Exceptions are caught and logged to stderr instead of propagating.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.infrastructure.database.models import AuditLogModel

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Writes immutable audit records.

    Injected into services that need audit trails.
    Requires an AsyncSession — one audit log per request session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        action: AuditAction,
        *,
        org_id: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Append one audit record.
        Never raises — failures are swallowed and logged to stderr.
        """
        rid = request_id or str(uuid.uuid4())

        record = AuditLogModel(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=rid,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )

        bound = logger.bind(
            audit_action=action.value,
            org_id=org_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=rid,
        )

        try:
            self._session.add(record)
            await self._session.flush()     # Write within current transaction
            bound.info("audit_event")
        except Exception as exc:
            # Never let audit failures break the caller
            bound.error("audit_event_failed", error=str(exc))
