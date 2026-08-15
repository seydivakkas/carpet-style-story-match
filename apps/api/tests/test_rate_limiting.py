"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Integration tests for Rate Limiting Middleware.
"""
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.middleware import reset_rate_limiter


@pytest.fixture(autouse=True)
def auto_reset_rate_limiter():
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.mark.asyncio
async def test_health_endpoint_exempt_from_rate_limiter(client: AsyncClient):
    old_limit = settings.RATE_LIMIT_PER_MINUTE
    old_flag = settings.ENABLE_RATE_LIMITER_IN_TEST
    settings.RATE_LIMIT_PER_MINUTE = 2
    settings.ENABLE_RATE_LIMITER_IN_TEST = True
    try:
        for _ in range(5):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
    finally:
        settings.RATE_LIMIT_PER_MINUTE = old_limit
        settings.ENABLE_RATE_LIMITER_IN_TEST = old_flag


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(client: AsyncClient):
    old_limit = settings.RATE_LIMIT_PER_MINUTE
    old_flag = settings.ENABLE_RATE_LIMITER_IN_TEST
    settings.RATE_LIMIT_PER_MINUTE = 3
    settings.ENABLE_RATE_LIMITER_IN_TEST = True
    try:
        # First 3 requests allowed
        for _ in range(3):
            resp = await client.get("/api/v1/carpets")
            assert resp.status_code in (200, 404)

        # 4th request exceeds limit -> 429
        over_resp = await client.get("/api/v1/carpets")
        assert over_resp.status_code == 429
        assert over_resp.headers.get("Retry-After") == "60"
        data = over_resp.json()
        assert data["detail"]["code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        settings.RATE_LIMIT_PER_MINUTE = old_limit
        settings.ENABLE_RATE_LIMITER_IN_TEST = old_flag
