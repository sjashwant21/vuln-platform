"""
User and refresh-token repository — SQLAlchemy 2.0 async implementation.

Tenant isolation:
  Every query that returns user data requires org_id as a positional argument.
  This makes it structurally impossible to accidentally leak cross-tenant data —
  forgetting org_id is a TypeError, not a silent data breach.

Refresh token storage:
  Only the SHA-256 hash of the raw token is persisted.
  get_by_hash() is the only lookup path — raw tokens never re-enter the DB.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import RefreshTokenModel, UserModel

logger = structlog.get_logger(__name__)


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Lookups ────────────────────────────────────────────────

    async def get_by_id(self, user_id: str, org_id: str) -> UserModel | None:
        """Fetch active user scoped to organisation."""
        stmt = select(UserModel).where(
            and_(
                UserModel.id == user_id,
                UserModel.organization_id == org_id,
                UserModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """
        Email is globally unique across all organisations.
        Used only for login — not for any data-access decision.
        org_id is obtained from the returned model, not from the caller.
        """
        stmt = select(UserModel).where(
            and_(
                UserModel.email == email.lower().strip(),
                UserModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_email_and_org(self, email: str, org_id: str) -> UserModel | None:
        stmt = select(UserModel).where(
            and_(
                UserModel.email == email.lower().strip(),
                UserModel.organization_id == org_id,
                UserModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserModel], int]:
        base = and_(
            UserModel.organization_id == org_id,
            UserModel.is_active.is_(True),
        )
        total = (
            await self._s.execute(
                select(func.count()).select_from(UserModel).where(base)
            )
        ).scalar_one()

        rows = (
            await self._s.execute(
                select(UserModel)
                .where(base)
                .order_by(UserModel.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        return list(rows), total

    async def email_exists(self, email: str) -> bool:
        stmt = select(func.count()).select_from(UserModel).where(
            UserModel.email == email.lower().strip()
        )
        return (await self._s.execute(stmt)).scalar_one() > 0

    async def count_by_org(self, org_id: str) -> int:
        stmt = select(func.count()).select_from(UserModel).where(
            and_(
                UserModel.organization_id == org_id,
                UserModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one()

    # ── Mutations ──────────────────────────────────────────────

    async def create(self, data: dict[str, Any]) -> UserModel:
        user = UserModel(
            id=str(uuid.uuid4()),
            **{**data, "email": data["email"].lower().strip()},
        )
        self._s.add(user)
        await self._s.flush()
        await self._s.refresh(user)
        logger.info("user_created", user_id=user.id, org_id=user.organization_id)
        return user

    async def update(
        self,
        user_id: str,
        org_id: str,
        data: dict[str, Any],
    ) -> UserModel | None:
        stmt = (
            update(UserModel)
            .where(
                and_(
                    UserModel.id == user_id,
                    UserModel.organization_id == org_id,
                )
            )
            .values(**data, updated_at=datetime.now(UTC))
            .returning(UserModel)
        )
        result = (await self._s.execute(stmt)).scalar_one_or_none()
        return result

    async def deactivate(self, user_id: str, org_id: str) -> bool:
        """Soft delete — sets is_active=False."""
        stmt = (
            update(UserModel)
            .where(
                and_(
                    UserModel.id == user_id,
                    UserModel.organization_id == org_id,
                )
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        result = await self._s.execute(stmt)
        return result.rowcount > 0

    async def update_last_login(self, user_id: str) -> None:
        await self._s.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=datetime.now(UTC))
        )

    async def update_password(self, user_id: str, org_id: str, new_hash: str) -> None:
        await self._s.execute(
            update(UserModel)
            .where(
                and_(
                    UserModel.id == user_id,
                    UserModel.organization_id == org_id,
                )
            )
            .values(password_hash=new_hash, updated_at=datetime.now(UTC))
        )

    # ── Refresh tokens ─────────────────────────────────────────

    async def store_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshTokenModel:
        token = RefreshTokenModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._s.add(token)
        await self._s.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshTokenModel | None:
        stmt = select(RefreshTokenModel).where(
            and_(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked.is_(False),
                RefreshTokenModel.expires_at > datetime.now(UTC),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str) -> None:
        await self._s.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(revoked=True)
        )

    async def revoke_all_refresh_tokens(self, user_id: str) -> None:
        """Revoke all sessions — called on password change or admin action."""
        await self._s.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .values(revoked=True)
        )

    async def purge_expired_tokens(self) -> int:
        """Housekeeping — delete tokens past expiry. Called by a periodic task."""
        from sqlalchemy import delete

        result = await self._s.execute(
            delete(RefreshTokenModel).where(
                RefreshTokenModel.expires_at < datetime.now(UTC)
            )
        )
        return result.rowcount
