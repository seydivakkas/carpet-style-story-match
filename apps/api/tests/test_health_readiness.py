"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Integration tests for Liveness & Readiness Endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_liveness_endpoints(client: AsyncClient):
    resp1 = await client.get("/api/v1/health")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "ok"

    resp2 = await client.get("/api/v1/health/live")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_endpoint_healthy(client: AsyncClient):
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "healthy"
    assert data["storage"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_fails(client: AsyncClient):
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("DB Connection Refused")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "unhealthy"
    finally:
        app.dependency_overrides.pop(get_db, None)
