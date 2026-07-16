"""
Application configuration.

All values come from environment variables or .env file.
Validated by Pydantic at startup — bad config fails fast with clear messages.
The @lru_cache ensures settings are parsed exactly once per process.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application -------------------------------------------
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "VulnAssess Platform"
    app_version: str = "1.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    secret_key: str = Field(..., min_length=32)

    # -- API ---------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_workers: int = Field(default=4, ge=1, le=32)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return [o.strip() for o in v if o.strip()]
        if isinstance(v, str):
            v = v.strip()
            # Try JSON array format first: ["url1","url2"]
            if v.startswith("["):
                try:
                    import json
                    parsed = json.loads(v)
                    return [o.strip() for o in parsed if o.strip()]
                except Exception:
                    pass
            # Fall back to comma-separated
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # -- JWT ---------------------------------------------------
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=15, ge=5, le=60)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=30)

    # -- Database ----------------------------------------------
    database_url: str = Field(...)
    database_pool_size: int = Field(default=20, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5, le=300)

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    # -- Redis -------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # -- Security ----------------------------------------------
    bcrypt_rounds: int = Field(default=12, ge=10, le=14)
    mfa_issuer: str = "VulnAssessPlatform"
    rate_limit_per_minute: int = Field(default=60, ge=1)

    # -- External services -------------------------------------
    # Groq (free AI provider — replaces Anthropic)
    groq_api_key: str = Field(default="")
    groq_model: str = "llama3-70b-8192"

    # Anthropic (optional, leave empty if using Groq)
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # NVD (National Vulnerability Database)
    nvd_api_key: str | None = None
    nvd_api_base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    nvd_rate_limit_delay: float = Field(default=0.6, ge=0.0)  # seconds; 0.6s = ~50req/30s

    # -- Derived properties ------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def database_url_sync(self) -> str:
        """Synchronous URL for Alembic migrations (uses psycopg2)."""
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        ).replace("postgresql://", "postgresql+psycopg2://")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached application settings.
    Import and call this everywhere instead of instantiating Settings directly.
    """
    return Settings()  # type: ignore[call-arg]
