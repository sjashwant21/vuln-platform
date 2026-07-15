"""
Password hashing and verification using bcrypt.

Security notes:
  - Work factor 12 is the production minimum (~250ms on modern hardware)
  - passlib.CryptContext handles algorithm upgrades transparently
  - needs_rehash() enables silent upgrades on login when rounds change
  - All comparisons are constant-time (passlib guarantees this)
"""
from __future__ import annotations

from passlib.context import CryptContext

from app.config import get_settings


class PasswordHandler:
    """
    Wraps passlib CryptContext for bcrypt hashing.

    Instantiate once and reuse — CryptContext creation is slightly expensive.
    The FastAPI DI system handles this via a module-level instance.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._ctx = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.bcrypt_rounds,
        )

    def hash(self, plain: str) -> str:
        """
        Return a bcrypt hash of the plaintext password.
        The hash includes the salt and work factor — safe to store directly.
        """
        return self._ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        """
        Constant-time comparison of plaintext against stored bcrypt hash.
        Returns False (not raises) on any mismatch — callers decide how to respond.
        """
        return self._ctx.verify(plain, hashed)

    def needs_rehash(self, hashed: str) -> bool:
        """
        True when the stored hash was produced with different parameters
        (e.g. lower bcrypt rounds). Call after successful login to silently
        upgrade legacy hashes.
        """
        return self._ctx.needs_update(hashed)


# Module-level singleton — import this instead of instantiating directly
password_handler = PasswordHandler()
