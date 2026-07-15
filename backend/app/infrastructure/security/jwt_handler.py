"""
JWT access token creation + verification, and opaque refresh token management.

Token design:
  Access token  — signed JWT, short-lived (15 min), contains user claims
  Refresh token — opaque random string (urlsafe-base64, 64 bytes entropy)
                  Only the SHA-256 hash is stored in the DB.
                  Rotated on every use — stolen token is invalidated after first use.

Claims in access token payload:
  sub   — user ID
  org   — organization ID
  role  — UserRole value
  email — user email (for display, never for auth decisions)
  type  — "access" (guard against using refresh JWTs as access, if JWT refresh is ever added)
  jti   — unique token ID (enables blocklist if needed in future)
  iat / exp — standard claims
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings
from app.domain.exceptions import InvalidTokenError, TokenExpiredError


class JWTHandler:

    ACCESS_TOKEN_TYPE  = "access"

    def __init__(self) -> None:
        self._cfg = get_settings()

    # ── Access tokens ──────────────────────────────────────────

    def create_access_token(
        self,
        user_id: str,
        org_id: str,
        role: str,
        email: str,
    ) -> str:
        """Sign and return a JWT access token."""
        now    = datetime.now(UTC)
        expire = now + timedelta(minutes=self._cfg.jwt_access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub":   user_id,
            "org":   org_id,
            "role":  role,
            "email": email,
            "type":  self.ACCESS_TOKEN_TYPE,
            "jti":   secrets.token_hex(16),
            "iat":   now,
            "exp":   expire,
        }

        return jwt.encode(
            payload,
            self._cfg.jwt_secret_key,
            algorithm=self._cfg.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """
        Verify signature + expiry and return the decoded payload.

        Raises:
            TokenExpiredError   — token past its exp claim
            InvalidTokenError   — bad signature, malformed, wrong type
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._cfg.jwt_secret_key,
                algorithms=[self._cfg.jwt_algorithm],
                options={"verify_exp": True},
            )
        except JWTError as exc:
            msg = str(exc).lower()
            if "expired" in msg or "exp" in msg:
                raise TokenExpiredError() from exc
            raise InvalidTokenError(str(exc)) from exc

        if payload.get("type") != self.ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("Token type is not 'access'")

        return payload

    # ── Refresh tokens ─────────────────────────────────────────

    def create_refresh_token(self) -> tuple[str, str]:
        """
        Generate an opaque refresh token.

        Returns:
            (raw_token, sha256_hash)
            raw_token  — send to client in HttpOnly cookie / response body
            sha256_hash — store in database
        """
        raw   = secrets.token_urlsafe(64)
        hashed = self._hash(raw)
        return raw, hashed

    def hash_refresh_token(self, raw: str) -> str:
        """Hash a raw refresh token for database lookup."""
        return self._hash(raw)

    def refresh_token_expires_at(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=self._cfg.jwt_refresh_token_expire_days)

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()


# Module-level singleton
jwt_handler = JWTHandler()
