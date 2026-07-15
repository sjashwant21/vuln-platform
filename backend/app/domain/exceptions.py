"""
Domain exception hierarchy.

These are pure domain exceptions — zero HTTP/framework coupling.
The API layer maps them to HTTP responses via exception handlers registered
in main.py. This means domain logic never imports from FastAPI.

Hierarchy:
  VulnAssessError
  ├── AuthenticationError
  │   ├── TokenExpiredError
  │   ├── InvalidTokenError
  │   ├── MFARequiredError
  │   └── MFAInvalidError
  ├── AuthorizationError
  │   └── InsufficientRoleError
  ├── ResourceNotFoundError
  ├── ResourceConflictError
  ├── TenantIsolationError
  ├── ValidationError
  │   ├── InvalidIPAddressError
  │   └── InvalidCIDRError
  ├── PlanLimitError
  └── ExternalServiceError
      ├── NVDAPIError
      ├── AnthropicAPIError
      └── RateLimitError
"""
from __future__ import annotations


class VulnAssessError(Exception):
    """Base class for all application errors."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or message


# ── Authentication ─────────────────────────────────────────────

class AuthenticationError(VulnAssessError):
    """Credentials invalid or token unusable."""


class TokenExpiredError(AuthenticationError):
    """JWT access token has passed its expiry."""

    def __init__(self) -> None:
        super().__init__("Access token has expired", "Please refresh your token")


class InvalidTokenError(AuthenticationError):
    """JWT signature invalid, malformed, or wrong type."""

    def __init__(self, reason: str = "Token is invalid") -> None:
        super().__init__(reason)


class MFARequiredError(AuthenticationError):
    """This account requires MFA verification to proceed."""

    def __init__(self) -> None:
        super().__init__(
            "Multi-factor authentication is required",
            "Please complete MFA verification",
        )


class MFAInvalidError(AuthenticationError):
    """Provided TOTP code is incorrect or expired."""

    def __init__(self) -> None:
        super().__init__("Invalid MFA code", "The provided code is incorrect or has expired")


# ── Authorization ──────────────────────────────────────────────

class AuthorizationError(VulnAssessError):
    """Caller is authenticated but lacks permission."""


class InsufficientRoleError(AuthorizationError):
    """User's role does not permit this operation."""

    def __init__(self, required: str, current: str) -> None:
        super().__init__(
            f"Role '{required}' required, current role is '{current}'",
            "You do not have permission to perform this action",
        )
        self.required_role = required
        self.current_role = current


class TenantIsolationError(AuthorizationError):
    """Attempt to access another organisation's resource."""

    def __init__(self) -> None:
        super().__init__(
            "Cross-tenant resource access denied",
            "You do not have access to this resource",
        )


# ── Resource errors ────────────────────────────────────────────

class ResourceNotFoundError(VulnAssessError):
    """Requested resource does not exist (or is invisible to this tenant)."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            f"{resource_type} '{identifier}' not found",
            f"The requested {resource_type.lower()} does not exist",
        )
        self.resource_type = resource_type
        self.identifier = identifier


class ResourceConflictError(VulnAssessError):
    """Resource already exists or would violate a uniqueness constraint."""

    def __init__(self, resource_type: str, field: str, value: str) -> None:
        super().__init__(
            f"{resource_type} with {field}='{value}' already exists",
        )
        self.resource_type = resource_type
        self.field = field
        self.value = value


# ── Validation errors ──────────────────────────────────────────

class ValidationError(VulnAssessError):
    """Input data failed domain-level validation."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Validation failed on '{field}': {message}")
        self.field = field


class InvalidIPAddressError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__("ip_address", f"'{value}' is not a valid IPv4 or IPv6 address")


class InvalidCIDRError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__("cidr", f"'{value}' is not a valid CIDR range")


# ── Plan / quota ───────────────────────────────────────────────

class PlanLimitError(VulnAssessError):
    """Operation would exceed the organisation's plan quota."""

    def __init__(self, feature: str, limit: int, current: int) -> None:
        super().__init__(
            f"Plan limit exceeded for '{feature}': {current}/{limit}",
            f"Upgrade your plan to increase the {feature} limit",
        )
        self.feature = feature
        self.limit = limit
        self.current = current


# ── External service errors ────────────────────────────────────

class ExternalServiceError(VulnAssessError):
    """An external API call failed."""

    def __init__(self, service: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
        self.status_code = status_code


class NVDAPIError(ExternalServiceError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__("NVD", message, status_code)


class AnthropicAPIError(ExternalServiceError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__("Anthropic", message, status_code)


class RateLimitError(ExternalServiceError):
    def __init__(self, service: str, retry_after: int | None = None) -> None:
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(service, msg)
        self.retry_after = retry_after


# ── Scan errors ────────────────────────────────────────────────

class ScanError(VulnAssessError):
    """Base for scan-related failures."""


class ScanTargetError(ScanError):
    def __init__(self, target: str, reason: str) -> None:
        super().__init__(f"Invalid scan target '{target}': {reason}")
        self.target = target


class ScanLimitError(ScanError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Concurrent scan limit ({limit}) reached",
            "Wait for existing scans to complete or upgrade your plan",
        )
        self.limit = limit
