"""Dağıtık Redis hız sınırı: işçiler arasında atomik kota ve ayrıştırma."""
import os
import pytest

if os.getenv('CARPET_RUN_REDIS_TESTS') != '1':
    pytest.skip('Redis entegrasyonu ayrı gerçek Redis CI işinde koşar.', allow_module_level=True)
from app.core.shared_rate_limit import acquire_redis_quota, get_redis_client

@pytest.mark.asyncio
async def test_redis_shared_quota_atomic_and_isolates_clients():
    url = "redis://127.0.0.1:6379/15"
    redis = get_redis_client(url)
    await redis.flushdb()
    try:
        assert await acquire_redis_quota(url, "client-A", max_requests=2)
        assert await acquire_redis_quota(url, "client-A", max_requests=2)
        assert not await acquire_redis_quota(url, "client-A", max_requests=2)
        assert await acquire_redis_quota(url, "client-B", max_requests=2)
        keys = await redis.keys("carpet:rl:v1:*")
        assert len(keys) == 2
        assert b"client-A" not in b"".join(keys)
    finally:
        await redis.flushdb()

@pytest.mark.asyncio
async def test_redis_limiter_concurrent_requests_have_single_winner():
    import asyncio
    url = "redis://127.0.0.1:6379/15"
    redis = get_redis_client(url)
    await redis.flushdb()
    try:
        results = await asyncio.gather(*[
            acquire_redis_quota(url, "same-client", max_requests=1) for _ in range(20)
        ])
        assert sum(results) == 1
    finally:
        await redis.flushdb()
