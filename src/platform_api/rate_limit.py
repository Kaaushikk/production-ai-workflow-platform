import logging
import time
from typing import Annotated, Protocol, cast

from fastapi import Depends, HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from platform_api.auth import TenantDep

logger = logging.getLogger(__name__)

INCREMENT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class RateLimiter(Protocol):
    def allow(self, tenant_id: str) -> bool: ...

    def close(self) -> None: ...


class NullRateLimiter:
    def allow(self, tenant_id: str) -> bool:
        del tenant_id
        return True

    def close(self) -> None:
        pass


class RedisRateLimiter:
    def __init__(self, url: str, limit: int, window_seconds: int) -> None:
        self._client = Redis.from_url(url, decode_responses=True, socket_timeout=1)
        self._limit = limit
        self._window_seconds = window_seconds

    def allow(self, tenant_id: str) -> bool:
        bucket = int(time.time()) // self._window_seconds
        key = f"rate-limit:{tenant_id}:{bucket}"
        result = cast(
            str | int,
            self._client.eval(INCREMENT_SCRIPT, 1, key, str(self._window_seconds)),
        )
        count = int(result)
        return count <= self._limit

    def close(self) -> None:
        self._client.close()


def build_rate_limiter(url: str, limit: int, window_seconds: int) -> RateLimiter:
    if not url.strip():
        return NullRateLimiter()
    return RedisRateLimiter(url, limit, window_seconds)


def enforce_rate_limit(request: Request, tenant: TenantDep) -> None:
    limiter = cast(RateLimiter, request.app.state.rate_limiter)
    try:
        allowed = limiter.allow(str(tenant.id))
    except RedisError:
        logger.exception("rate_limiter_unavailable", extra={"tenant_id": str(tenant.id)})
        return
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(request.app.state.settings.rate_limit_window_seconds)
            },
        )


RateLimitDep = Annotated[None, Depends(enforce_rate_limit)]
