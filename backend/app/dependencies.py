"""
FastAPI dependency injection container.

All injectables are defined here as async generator or regular functions.
FastAPI resolves the dependency graph automatically — you declare what you
need in the function signature and FastAPI wires it up.

Dependency tree (simplified):
  get_db_session          ← AsyncSession (per-request)
    └── get_user_repo     ← UserRepository(session)
    └── get_org_repo      ← OrganizationRepository(session)
    └── get_audit_logger  ← AuditLogger(session)
        └── get_auth_service ← AuthService(repos, handlers, audit)
        └── get_user_service ← UserService(repos, audit)
        └── get_org_service  ← OrganizationService(repo, audit)

  get_current_user        ← decodes JWT, returns AuthenticatedUser
    └── require_role(...)  ← RBAC guard factory
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.auth_dto import AuthenticatedUser
from app.application.services.auth_service import AuthService
from app.application.services.organization_service import OrganizationService
from app.application.services.user_service import UserService
from app.domain.enums import UserRole
from app.domain.exceptions import (
    AuthenticationError,
    InsufficientRoleError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.audit_logger import AuditLogger
from app.infrastructure.security.jwt_handler import jwt_handler
from app.infrastructure.security.password_handler import password_handler

logger = structlog.get_logger(__name__)

# ── HTTP Bearer scheme (auto-generates OpenAPI security schema) ─
_bearer = HTTPBearer(auto_error=False)

# ── Type aliases for cleaner signatures ────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Repository factories ────────────────────────────────────────

def get_user_repo(db: DBSession) -> UserRepository:
    return UserRepository(db)


def get_org_repo(db: DBSession) -> OrganizationRepository:
    return OrganizationRepository(db)


def get_audit_logger(db: DBSession) -> AuditLogger:
    return AuditLogger(db)


# ── Service factories ───────────────────────────────────────────

def get_auth_service(
    db: DBSession,
    user_repo: Annotated[UserRepository,      Depends(get_user_repo)],
    org_repo:  Annotated[OrganizationRepository, Depends(get_org_repo)],
    audit:     Annotated[AuditLogger,          Depends(get_audit_logger)],
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        org_repo=org_repo,
        password_handler=password_handler,
        jwt_handler=jwt_handler,
        audit=audit,
    )


def get_user_service(
    user_repo: Annotated[UserRepository,         Depends(get_user_repo)],
    org_repo:  Annotated[OrganizationRepository, Depends(get_org_repo)],
    audit:     Annotated[AuditLogger,            Depends(get_audit_logger)],
) -> UserService:
    return UserService(user_repo=user_repo, org_repo=org_repo, audit=audit)


def get_org_service(
    org_repo: Annotated[OrganizationRepository, Depends(get_org_repo)],
    audit:    Annotated[AuditLogger,            Depends(get_audit_logger)],
) -> OrganizationService:
    return OrganizationService(org_repo=org_repo, audit=audit)


# ── Authentication guard ────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """
    Decode and validate the JWT Bearer token from the Authorization header.
    Injects an AuthenticatedUser into any route that declares this dependency.

    Raises HTTP 401 if token is missing, expired, or invalid.
    The exception is caught by the global exception handler in main.py.
    """
    if credentials is None:
        raise AuthenticationError("Authorization header is missing or malformed")

    payload = jwt_handler.decode_access_token(credentials.credentials)

    user = AuthenticatedUser(
        user_id=payload["sub"],
        org_id=payload["org"],
        role=payload["role"],
        email=payload["email"],
    )

    # Bind user context to structlog for the rest of this request
    structlog.contextvars.bind_contextvars(
        user_id=user.user_id,
        org_id=user.org_id,
        role=user.role,
    )

    return user


# ── RBAC role guard factory ────────────────────────────────────

def require_role(*allowed_roles: UserRole):
    """
    Dependency factory that enforces minimum role.

    Usage:
        @router.post("/scans")
        async def create_scan(
            _: Annotated[None, Depends(require_role(UserRole.ANALYST))],
            current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
        ):
            ...
    """
    async def _guard(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> None:
        try:
            user_role = UserRole(current_user.role)
        except ValueError:
            raise InsufficientRoleError(
                required=allowed_roles[0].value,
                current=current_user.role,
            )

        if user_role not in allowed_roles:
            raise InsufficientRoleError(
                required=" or ".join(r.value for r in allowed_roles),
                current=current_user.role,
            )

    return _guard


# ── Convenience type aliases for route signatures ──────────────

CurrentUser  = Annotated[AuthenticatedUser, Depends(get_current_user)]
AuthSvc      = Annotated[AuthService,       Depends(get_auth_service)]
UserSvc      = Annotated[UserService,       Depends(get_user_service)]
OrgSvc       = Annotated[OrganizationService, Depends(get_org_service)]
