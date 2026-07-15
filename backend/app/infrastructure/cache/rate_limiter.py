"""
Redis-backed token bucket rate limiter.

Shared across all API workers and Celery workers via Redis.
This is critical for NVD compliance — a per-process limiter would allow
N workers × rate_limit requests, blowing through NVD's quota.

Token bucket algorithm:
  - Bucket holds up to `capacity` tokens
  - Refills at `refill_rate` tokens/second
  - Each request consumes 1 token
  - If bucket is empty → caller must wait

The entire acquire/refill cycle is executed as a Lua script inside Redis,
making it atomic without requiring WATCH/MULTI/EXEC transactions.
"""
from __future__ import annotations

import asyncio
import time
from typing import NamedTuple

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)

# Atomic Lua script: refill tokens, then try to consume one.
# Returns [tokens_remaining, wait_ms]
#   wait_ms = 0  → token acquired, proceed immediately
#   wait_ms > 0  → bucket empty, caller must sleep this many milliseconds
_LUA_TOKEN_BUCKET = """
local key          = KEYS[1]
local capacity     = tonumber(ARGV[1])
local refill_rate  = tonumber(ARGV[2])   -- tokens per second
local now_ms       = tonumber(ARGV[3])   -- current epoch milliseconds

-- Read current state
local state = redis.call('HMGET', key, 'tokens', 'last_refill_ms')
local tokens        = tonumber(state[1]) or capacity
local last_refill   = tonumber(state[2]) or now_ms

-- Refill based on elapsed time
local elapsed_sec  = (now_ms - last_refill) / 1000.0
local new_tokens   = math.min(capacity, tokens + (elapsed_sec * refill_rate))

-- Try to consume one token
local wait_ms = 0
if new_tokens >= 1 then
    new_tokens = new_tokens - 1
else
    -- Calculate how long until next token is available
    local deficit  = 1 - new_tokens
    wait_ms        = math.ceil((deficit / refill_rate) * 1000)
end

-- Persist updated state with TTL slightly longer than full refill time
local ttl_sec = math.ceil(capacity / refill_rate) + 10
redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill_ms', now_ms)
redis.call('EXPIRE', key, ttl_sec)

return {math.floor(new_tokens), wait_ms}
"""


class TokenBucketResult(NamedTuple):
    acquired:         bool
    tokens_remaining: int
    wait_ms:          int   # how long to wait if not acquired


class RedisTokenBucket:
    """
    Token bucket rate limiter backed by Redis.

    Usage:
        limiter = RedisTokenBucket(redis_client, "nvd_api", capacity=50, refill_rate=50/30)
        result = await limiter.acquire()
        if not result.acquired:
            await asyncio.sleep(result.wait_ms / 1000)
            result = await limiter.acquire()
    """

    def __init__(
        self,
        redis: aioredis.Redis,       # type: ignore[type-arg]
        key:   str,
        capacity:     float,          # max tokens in bucket
        refill_rate:  float,          # tokens per second
    ) -> None:
        self._redis       = redis
        self._key         = f"rate_limiter:{key}"
        self._capacity    = capacity
        self._refill_rate = refill_rate
        self._script      = self._redis.register_script(_LUA_TOKEN_BUCKET)

    async def acquire(self, *, max_wait_ms: int = 35_000) -> TokenBucketResult:
        """
        Try to acquire one token.

        If the bucket is temporarily empty and max_wait_ms > 0,
        this method will sleep and retry automatically.

        Returns TokenBucketResult(acquired=True) on success.
        Raises TimeoutError if waiting would exceed max_wait_ms.
        """
        total_waited_ms = 0

        while True:
            now_ms = int(time.time() * 1000)
            result = await self._script(
                keys=[self._key],
                args=[self._capacity, self._refill_rate, now_ms],
            )
            tokens_remaining = int(result[0])
            wait_ms          = int(result[1])

            if wait_ms == 0:
                return TokenBucketResult(acquired=True, tokens_remaining=tokens_remaining, wait_ms=0)

            # Bucket empty
            if total_waited_ms + wait_ms > max_wait_ms:
                logger.warning(
                    "rate_limiter_timeout",
                    key=self._key,
                    waited_ms=total_waited_ms,
                    requested_wait=wait_ms,
                )
                raise TimeoutError(
                    f"Rate limiter '{self._key}' would require waiting "
                    f"{total_waited_ms + wait_ms}ms, exceeding limit of {max_wait_ms}ms"
                )

            logger.debug(
                "rate_limiter_waiting",
                key=self._key,
                wait_ms=wait_ms,
                tokens_remaining=tokens_remaining,
            )
            await asyncio.sleep(wait_ms / 1000.0)
            total_waited_ms += wait_ms

    async def current_tokens(self) -> float:
        """Inspect current token count without consuming."""
        state = await self._redis.hmget(self._key, "tokens", "last_refill_ms")
        tokens      = float(state[0]) if state[0] else self._capacity
        last_refill = float(state[1]) if state[1] else time.time() * 1000
        elapsed     = (time.time() * 1000 - last_refill) / 1000.0
        return min(self._capacity, tokens + elapsed * self._refill_rate)

    async def reset(self) -> None:
        """Reset bucket to full (useful in tests)."""
        await self._redis.delete(self._key)
