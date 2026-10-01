import uuid
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from platform_api.auth import TenantContext
from platform_api.config import Settings
from platform_api.rate_limit import NullRateLimiter, RedisRateLimiter, enforce_rate_limit


def test_null_rate_limiter_allows_offline_development() -> None:
    limiter = NullRateLimiter()

    assert limiter.allow("tenant-1") is True
    limiter.close()


def test_redis_rate_limiter_enforces_configured_fixed_window() -> None:
    limiter = RedisRateLimiter.__new__(RedisRateLimiter)
    limiter._client = Mock()  # type: ignore[attr-defined]
    limiter._client.eval.side_effect = [1, 2, 3]  # type: ignore[attr-defined]
    limiter._limit = 2  # type: ignore[attr-defined]
    limiter._window_seconds = 60  # type: ignore[attr-defined]

    assert limiter.allow("tenant-1") is True
    assert limiter.allow("tenant-1") is True
    assert limiter.allow("tenant-1") is False


def test_dependency_rejects_excess_requests_and_fails_open_without_redis() -> None:
    tenant = TenantContext(id=uuid.uuid4(), slug="tenant-1")
    request = Mock()
    request.app.state.settings = Settings(_env_file=None, rate_limit_window_seconds=30)
    request.app.state.rate_limiter.allow.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(request, tenant)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "30"}

    request.app.state.rate_limiter.allow.side_effect = ConnectionError("offline")
    enforce_rate_limit(request, tenant)
