"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Integration tests for Request Security, Headers, and Correlation IDs.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_correlation_id_generation_and_propagation(client: AsyncClient):
    # Case 1: Client provides valid X-Request-ID
    custom_id = "test-req-id-12345"
    resp1 = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Request-ID") == custom_id

    # Case 2: Client provides no X-Request-ID -> server generates one
    resp2 = await client.get("/api/v1/health")
    assert resp2.status_code == 200
    generated_id = resp2.headers.get("X-Request-ID")
    assert generated_id is not None
    assert generated_id.startswith("req_")


@pytest.mark.asyncio
async def test_invalid_correlation_id_replaced_with_safe_uuid(client: AsyncClient):
    malicious_id = "<script>alert('xss')</script>"
    resp = await client.get("/api/v1/health", headers={"X-Request-ID": malicious_id})
    assert resp.status_code == 200
    returned_id = resp.headers.get("X-Request-ID")
    assert returned_id != malicious_id
    assert returned_id.startswith("req_")


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("X-Frame-Options") == "DENY"
