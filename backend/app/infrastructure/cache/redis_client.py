"""
Redis client wrapper with connection pooling.
Provides typed helper methods for common cache operations.
"""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


def get_redis_client() -> aioredis.Redis:  # type: ignore[type-arg]
    """Return (or create) the shared Redis client with connection pooling."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


class CacheClient:
    """
    High-level cache operations with JSON serialization.
    All keys are namespaced to prevent collisions.
    """

    NAMESPACE_SEPARATOR = ":"

    def __init__(self, namespace: str) -> None:
        self._namespace = namespace
        self._redis = get_redis_client()

    def _key(self, key: str) -> str:
        return f"{self._namespace}{self.NAMESPACE_SEPARATOR}{key}"

    async def get(self, key: str) -> Any | None:
        """Get a JSON-deserialized value."""
        raw = await self._redis.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta | int | None = None,
    ) -> None:
        """Set a JSON-serialized value with optional TTL."""
        serialized = json.dumps(value, default=str)
        if ttl is not None:
            seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl
            await self._redis.setex(self._key(key), seconds, serialized)
        else:
            await self._redis.set(self._key(key), serialized)

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        result = await self._redis.delete(self._key(key))
        return bool(result)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(self._key(key)))

    async def increment(self, key: str, amount: int = 1) -> int:
        return int(await self._redis.incrby(self._key(key), amount))

    async def expire(self, key: str, ttl: timedelta | int) -> None:
        seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl
        await self._redis.expire(self._key(key), seconds)

    async def get_or_set(
        self,
        key: str,
        factory: Any,  # Callable[[], Awaitable[Any]]
        ttl: timedelta | int,
    ) -> Any:
        """
        Cache-aside pattern: get from cache or compute and store.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value
