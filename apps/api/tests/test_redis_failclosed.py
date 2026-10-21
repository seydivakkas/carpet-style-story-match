"""Paylaşımlı Redis kesintisinde üretim hız sınırı hiçbir isteği serbest bırakmaz."""
import pytest
from app.core.config import settings
from app.core import middleware as middleware_module

@pytest.mark.asyncio
async def test_unavailable_distributed_quota_fails_closed(client, monkeypatch):
    async def broken_quota(*args, **kwargs):
        raise ConnectionError("redis is down")

    previous = (settings.RATE_LIMIT_BACKEND, settings.REDIS_URL,
                settings.ENABLE_RATE_LIMITER_IN_TEST)
    settings.RATE_LIMIT_BACKEND = "redis"
    settings.REDIS_URL = "redis://127.0.0.1:6379/0"
    settings.ENABLE_RATE_LIMITER_IN_TEST = True
    monkeypatch.setattr(middleware_module, "acquire_redis_quota", broken_quota)
    try:
        response = await client.get("/api/v1/carpets")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "RATE_LIMIT_UNAVAILABLE"
    finally:
        (settings.RATE_LIMIT_BACKEND, settings.REDIS_URL,
         settings.ENABLE_RATE_LIMITER_IN_TEST) = previous
