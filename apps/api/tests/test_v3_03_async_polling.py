"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Async Polling & Background Task Unit Tests (Phase P5).
Tests:
1. End-to-end POST 202 -> status poll -> GET 5-card result.
2. Unknown UUID status poll -> 404.
3. Quality block persistence (BLOCKED_BY_QUALITY).
4. Startup reaper for stale PROCESSING records.
5. Background task exception isolation.
"""
import uuid
import asyncio
import pytest
import numpy as np
import cv2
from unittest.mock import patch

from sqlalchemy import select
from httpx import AsyncClient

from app.core.config import settings
from app.main import reap_stale_processing_analyses
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum


def create_dummy_jpeg_bytes(width: int = 100, height: int = 100, color=(128, 64, 32)) -> bytes:
    """Helper creating valid JPEG bytes."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, encoded_img = cv2.imencode(".jpg", img)
    if not success:
        raise RuntimeError("Failed to encode synthetic JPEG image")
    return encoded_img.tobytes()


async def poll_status_until_terminal(client: AsyncClient, aid: str, max_retries: int = 50) -> dict:
    """Polls status endpoint asynchronously until status is no longer PROCESSING."""
    for _ in range(max_retries):
        res = await client.get(f"/api/v1/upload-analysis/{aid}/status")
        assert res.status_code == 200
        data = res.json()
        if data["status"] != "PROCESSING":
            return data
        await asyncio.sleep(0.1)
    return (await client.get(f"/api/v1/upload-analysis/{aid}/status")).json()


@pytest.mark.asyncio
async def test_p5_01_e2e_async_polling_flow(client: AsyncClient):
    """1. End-to-end flow: POST image -> 202 Accepted -> GET status COMPLETED -> GET 5-card result 200."""
    old_provider = settings.MOTIF_VLM_PROVIDER
    settings.MOTIF_VLM_PROVIDER = "TEST_FIXTURE"
    try:
        jpeg_bytes = create_dummy_jpeg_bytes()
        files = {"file": ("test_carpet.jpg", jpeg_bytes, "image/jpeg")}

        # POST enqueues background task and returns 202 immediately
        post_res = await client.post("/api/v1/upload-analysis/unified-result", files=files)
        assert post_res.status_code == 202
        data = post_res.json()
        assert "analysis_id" in data
        assert data["status"] == "PROCESSING"
        aid = data["analysis_id"]

        # Background task completes asynchronously, status becomes COMPLETED
        status_data = await poll_status_until_terminal(client, aid)
        assert status_data["analysis_id"] == aid
        assert status_data["status"] == "COMPLETED"

        # GET unified-result returns 200 and 5 cards
        result_res = await client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
        assert result_res.status_code == 200
        res_json = result_res.json()
        assert res_json["analysis_id"] == aid
        assert "visual_character" in res_json
        assert "motifs" in res_json
        assert "cultural_context" in res_json
        assert "motif_story" in res_json
        assert "historical_connections" in res_json
    finally:
        settings.MOTIF_VLM_PROVIDER = old_provider


@pytest.mark.asyncio
async def test_p5_02_unknown_uuid_returns_404(client: AsyncClient):
    """2. Unknown UUID polling returns 404."""
    random_id = str(uuid.uuid4())
    status_res = await client.get(f"/api/v1/upload-analysis/{random_id}/status")
    assert status_res.status_code == 404

    result_res = await client.get(f"/api/v1/upload-analysis/{random_id}/unified-result")
    assert result_res.status_code == 404


@pytest.mark.asyncio
async def test_p5_03_quality_block_persists_in_db(client: AsyncClient):
    """3. Corrupted image returns 202, background task persists BLOCKED_BY_QUALITY, GET result returns 200 with BLOCKED cards."""
    corrupted_bytes = b"NOT_A_VALID_JPEG_IMAGE_HEADER"
    files = {"file": ("bad_carpet.jpg", corrupted_bytes, "image/jpeg")}

    post_res = await client.post("/api/v1/upload-analysis/unified-result", files=files)
    assert post_res.status_code == 202
    aid = post_res.json()["analysis_id"]

    status_data = await poll_status_until_terminal(client, aid)
    assert status_data["status"] == "BLOCKED_BY_QUALITY"

    result_res = await client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
    assert result_res.status_code == 200
    res_json = result_res.json()
    assert res_json["visual_character"]["state"] == "BLOCKED_BY_QUALITY"


@pytest.mark.asyncio
async def test_p5_04_startup_reaper_cleans_stale_processing(db_session):
    """4. Startup reaper updates stale PROCESSING records to FAILED + error='server_restarted'."""
    stale_id = uuid.uuid4()
    stale_record = UploadAnalysisModel(
        id=stale_id,
        original_sha256="stale_hash",
        mime_type="image/jpeg",
        quality_status="PENDING",
        status=UploadAnalysisStatusEnum.PROCESSING
    )
    db_session.add(stale_record)
    await db_session.commit()

    # Call reaper with test session
    await reap_stale_processing_analyses(db_session)

    # Verify status changed to FAILED
    res = await db_session.execute(select(UploadAnalysisModel).where(UploadAnalysisModel.id == stale_id))
    rec = res.scalar_one()
    assert rec.status == UploadAnalysisStatusEnum.FAILED
    assert rec.error == "server_restarted"


@pytest.mark.asyncio
async def test_p5_05_background_task_exception_isolation(client: AsyncClient):
    """5. Unexpected orchestrator exception sets status FAILED and populates error string."""
    jpeg_bytes = create_dummy_jpeg_bytes()
    files = {"file": ("test_carpet.jpg", jpeg_bytes, "image/jpeg")}

    with patch("app.domain.orchestrator.service.UnifiedAnalysisOrchestrator.run_analysis", side_effect=RuntimeError("Simulated pipeline crash")):
        post_res = await client.post("/api/v1/upload-analysis/unified-result", files=files)
        assert post_res.status_code == 202
        aid = post_res.json()["analysis_id"]

        status_data = await poll_status_until_terminal(client, aid)
        assert status_data["status"] == "FAILED"
        assert "Simulated pipeline crash" in status_data["error"]

        result_res = await client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
        assert result_res.status_code == 409
