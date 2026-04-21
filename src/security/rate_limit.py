from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque
from typing import Protocol

import structlog
from fastapi import Header, HTTPException, Request
from redis import Redis

from src.config import settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


class RedisRateLimiter:
    def __init__(self, redis_url: str) -> None:
        self._redis = Redis.from_url(redis_url)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        count = int(self._redis.incr(key))
        if count == 1:
            self._redis.expire(key, window_seconds)
        return count <= limit


class _RateLimiterBackend(Protocol):
    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        ...


logger = structlog.get_logger("rate_limit")
_backend: _RateLimiterBackend
try:
    _backend = RedisRateLimiter(settings.redis_url)
except Exception as exc:
    logger.warning("rate_limiter_redis_init_failed", error=str(exc))
    _backend = InMemoryRateLimiter()


def _client_token(request: Request, authorization: str | None) -> str:
    auth = authorization or ""
    auth_digest = hashlib.sha256(auth.encode("utf-8")).hexdigest()[:16] if auth else "anon"
    ip = request.client.host if request.client else "unknown"
    return f"{auth_digest}:{ip}"


async def enforce_upload_rate_limit(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    if not settings.rate_limit_enabled:
        return

    token = _client_token(request, authorization)
    key = f"rl:upload:{token}"
    limit = max(settings.rate_limit_uploads_per_minute, 1)

    try:
        allowed = _backend.allow(key, limit=limit, window_seconds=60)
    except Exception as exc:
        # Fail open for demo resilience, but keep telemetry.
        logger.warning("rate_limiter_runtime_failed", error=str(exc))
        return

    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited")
