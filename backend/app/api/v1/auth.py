"""
Authentication router — /v1/auth/*

Routes are intentionally thin:
  - Parse + validate HTTP input (Pydantic handles this)
  - Extract HTTP context (IP, User-Agent) — only the HTTP layer knows these
  - Call the service
  - Return the response schema

All business logic, password policy, and token management live in AuthService.
"""

import ipaddress

import structlog
from fastapi import APIRouter, Request, status

from app.api.limiter import limiter
from app.api.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    OrganizationResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.application.dto.auth_dto import (
    ChangePasswordInput,
    LoginInput,
    RefreshInput,
    RegisterInput,
)
from app.dependencies import AuthSvc, CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# CIDRs of trusted reverse proxies (Nginx, ALB, Cloudflare, Railway, Render, Vercel)
_TRUSTED_PROXY_CIDRS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("10.0.0.0/8"),      # private (Kubernetes/Docker internal)
    ipaddress.ip_network("172.16.0.0/12"),   # private (Docker bridge)
    ipaddress.ip_network("192.168.0.0/16"),  # private (local)
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
]

# Account lockout settings
_MAX_LOGIN_FAILURES = 10
_LOCKOUT_SECONDS = 900  # 15 minutes


def _get_client_ip(request: Request) -> str:
    """
    Extract real client IP.

    Only trusts X-Forwarded-For when the direct connection comes from
    a known trusted proxy CIDR. This prevents IP spoofing by arbitrary
    clients setting their own X-Forwarded-For header.
    """
    direct_ip = request.client.host if request.client else "unknown"

    try:
        direct_addr = ipaddress.ip_address(direct_ip)
        is_trusted_proxy = any(direct_addr in net for net in _TRUSTED_PROXY_CIDRS)
        if is_trusted_proxy:
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                # Use the rightmost IP that we added — the first untrusted hop
                candidates = [ip.strip() for ip in forwarded_for.split(",")]
                # Walk right-to-left skipping trusted proxy IPs
                for candidate in reversed(candidates):
                    try:
                        candidate_addr = ipaddress.ip_address(candidate)
                        if not any(candidate_addr in net for net in _TRUSTED_PROXY_CIDRS):
                            return str(candidate_addr)
                    except ValueError:
                        continue
    except ValueError:
        pass

    return direct_ip


async def _check_account_lockout(email: str) -> None:
    """
    Raise AuthenticationError if this email has exceeded failed login attempts.
    Uses Redis if available; silently skips if Redis is unavailable.
    """
    try:
        import redis.asyncio as aioredis

        from app.config import get_settings
        from app.domain.exceptions import AuthenticationError as AuthErr

        cfg = get_settings()
        redis_client = aioredis.from_url(cfg.redis_url, socket_connect_timeout=1)
        key = f"login_fails:{email.lower()}"
        count = await redis_client.get(key)
        await redis_client.aclose()

        if count and int(count) >= _MAX_LOGIN_FAILURES:
            raise AuthErr(
                "Account temporarily locked due to too many failed login attempts. "
                "Try again in 15 minutes."
            )
    except Exception as exc:
        # Never let lockout checks crash the login flow
        if "locked" in str(exc).lower():
            raise
        logger.warning("lockout_check_skipped", error=str(exc))


async def _record_login_failure(email: str) -> None:
    """Increment failed login counter. Expires after lockout window."""
    try:
        import redis.asyncio as aioredis

        from app.config import get_settings

        cfg = get_settings()
        redis_client = aioredis.from_url(cfg.redis_url, socket_connect_timeout=1)
        key = f"login_fails:{email.lower()}"
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, _LOCKOUT_SECONDS)
        await pipe.execute()
        await redis_client.aclose()
    except Exception as exc:
        logger.warning("lockout_record_failed", error=str(exc))


async def _clear_login_failures(email: str) -> None:
    """Clear failed login counter on successful login."""
    try:
        import redis.asyncio as aioredis

        from app.config import get_settings

        cfg = get_settings()
        redis_client = aioredis.from_url(cfg.redis_url, socket_connect_timeout=1)
        await redis_client.delete(f"login_fails:{email.lower()}")
        await redis_client.aclose()
    except Exception as exc:
        logger.warning("lockout_clear_failed", error=str(exc))


# ── POST /auth/register ────────────────────────────────────────


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organisation and owner account",
)
@limiter.limit("5/minute")
async def register(
    body: RegisterRequest,
    service: AuthSvc,
    request: Request,
) -> RegisterResponse:
    user_dto, org_dto = await service.register(
        RegisterInput(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            organization_name=body.organization_name,
            organization_slug=body.organization_slug,
        )
    )
    # Issue a token pair immediately so the client doesn't need to login again
    tokens = await service.login(
        LoginInput(
            email=body.email,
            password=body.password,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    return RegisterResponse(
        user=UserResponse(
            id=user_dto.id,
            email=user_dto.email,
            full_name=user_dto.full_name,
            role=user_dto.role,
            mfa_enabled=user_dto.mfa_enabled,
            email_verified=user_dto.email_verified,
            created_at=user_dto.created_at,
            last_login_at=user_dto.last_login_at,
        ),
        organization=OrganizationResponse(
            id=org_dto.id,
            name=org_dto.name,
            slug=org_dto.slug,
            plan_tier=org_dto.plan_tier,
            max_assets=org_dto.max_assets,
            max_users=org_dto.max_users,
            max_concurrent_scans=org_dto.max_concurrent_scans,
            created_at=org_dto.created_at,
        ),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        ),
    )


# ── POST /auth/login ───────────────────────────────────────────


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    summary="Authenticate and receive an access token (refresh token in cookie)",
)
@limiter.limit("5/minute")
async def login(
    body: LoginRequest,
    service: AuthSvc,
    request: Request,
    response: Response,
) -> AccessTokenResponse:
    from fastapi import Response
    
    await _check_account_lockout(body.email)
    
    try:
        tokens = await service.login(
            LoginInput(
                email=body.email,
                password=body.password,
                ip_address=_get_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
            )
        )
        await _clear_login_failures(body.email)
    except Exception as exc:
        from app.domain.exceptions import AuthenticationError
        if isinstance(exc, AuthenticationError):
            await _record_login_failure(body.email)
        raise

    # Set refresh token as HttpOnly cookie
    from app.config import get_settings
    cfg = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=cfg.is_production,
        samesite="lax",
        max_age=cfg.jwt_refresh_token_expire_days * 24 * 3600,
        path="/v1/auth",  # Scoped to auth endpoints
    )

    return AccessTokenResponse(
        access_token=tokens.access_token,
    )


# ── POST /auth/refresh ─────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Rotate refresh token (from cookie) and get a new access token",
)
async def refresh_token(
    request: Request,
    service: AuthSvc,
    response: Response,
) -> AccessTokenResponse:
    from app.domain.exceptions import AuthenticationError
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthenticationError("Refresh token missing from cookies")
        
    tokens = await service.refresh(
        RefreshInput(
            refresh_token=refresh_token,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    
    # Set new refresh token as HttpOnly cookie
    from app.config import get_settings
    cfg = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=cfg.is_production,
        samesite="lax",
        max_age=cfg.jwt_refresh_token_expire_days * 24 * 3600,
        path="/v1/auth",
    )
    
    return AccessTokenResponse(
        access_token=tokens.access_token,
    )


# ── POST /auth/logout ──────────────────────────────────────────


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current refresh token",
)
async def logout(
    request: Request,
    service: AuthSvc,
    response: Response,
    current_user: CurrentUser,
) -> MessageResponse:
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await service.logout(
            refresh_token=refresh_token,
            current_user=current_user,
        )
    
    response.delete_cookie(key="refresh_token", path="/v1/auth")
    return MessageResponse(message="Logged out successfully")


# ── POST /auth/change-password ─────────────────────────────────


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the authenticated user's password",
)
async def change_password(
    body: ChangePasswordRequest,
    service: AuthSvc,
    current_user: CurrentUser,
) -> MessageResponse:
    await service.change_password(
        ChangePasswordInput(
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    )
    return MessageResponse(message="Password changed. All sessions have been revoked.")


# ── GET /auth/me ───────────────────────────────────────────────


@router.get(
    "/me",
    summary="Return the current user's identity from the JWT",
)
async def get_me(current_user: CurrentUser) -> dict:
    """Lightweight endpoint — decodes the token only, no DB hit."""
    return {
        "user_id": current_user.user_id,
        "org_id": current_user.org_id,
        "role": current_user.role,
        "email": current_user.email,
    }
