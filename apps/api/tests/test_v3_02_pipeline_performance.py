"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Performance and Offloading Tests for UnifiedAnalysisOrchestrator (Phase P4).
"""
import time
import asyncio
import pytest
import numpy as np
import cv2
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.domain.orchestrator.service import UnifiedAnalysisOrchestrator
from app.domain.upload_analysis.vlm_provider import VLMProviderError
from app.domain.result_experience.schemas import ResultSectionState


def create_dummy_jpeg_bytes(width: int = 100, height: int = 100, color=(128, 64, 32)) -> bytes:
    """Helper creating valid JPEG bytes."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, encoded_img = cv2.imencode(".jpg", img)
    if not success:
        raise RuntimeError("Failed to encode synthetic JPEG image")
    return encoded_img.tobytes()


@pytest.mark.asyncio
async def test_p4_01_parallel_execution_timing(db_session):
    """1. Parallel execution proof: 3 steps sleeping 0.2s run in < 0.45s total."""
    settings = Settings(MOTIF_VLM_PROVIDER="TEST_FIXTURE")
    orchestrator = UnifiedAnalysisOrchestrator(db=db_session, settings=settings)

    def mock_style_analyze(b):
        time.sleep(0.2)
        return "PASS", [{"key": "focal_strength", "value": 0.8}, {"key": "structural_order", "value": 0.7}]

    def mock_color_analyze(b):
        time.sleep(0.2)
        return []

    async def mock_vlm_analyze(prepared):
        await asyncio.sleep(0.2)
        mock_out = MagicMock()
        mock_out.motif_candidates = []
        mock_out.provenance.provider_type = "TEST_FIXTURE"
        return mock_out

    raw_bytes = create_dummy_jpeg_bytes()

    with patch.object(orchestrator.style_engine, "analyze", side_effect=mock_style_analyze), \
         patch.object(orchestrator.color_service, "analyze_colors", side_effect=mock_color_analyze), \
         patch("app.domain.orchestrator.service.get_vlm_provider") as mock_get_provider:

        mock_provider = MagicMock()
        mock_provider.analyze = mock_vlm_analyze
        mock_get_provider.return_value = mock_provider

        start_time = time.perf_counter()
        res = await orchestrator.run_analysis(raw_bytes=raw_bytes)
        elapsed = time.perf_counter() - start_time

        # Total sequential time would be >= 0.6s. Parallel execution must finish in < 0.45s.
        assert elapsed < 0.45, f"Pipeline took {elapsed:.3f}s, expected < 0.45s for parallel execution"
        assert res.visual_character.state == ResultSectionState.READY


@pytest.mark.asyncio
async def test_p4_02_output_equivalence(db_session):
    """2. Output equivalence: static synthetic image pipeline result fields match expected schemas."""
    settings = Settings(MOTIF_VLM_PROVIDER="DISABLED")
    orchestrator = UnifiedAnalysisOrchestrator(db=db_session, settings=settings)
    raw_bytes = create_dummy_jpeg_bytes()

    res = await orchestrator.run_analysis(raw_bytes=raw_bytes)

    assert res.visual_character.state == ResultSectionState.READY
    assert len(res.visual_character.palette) > 0
    assert "central_focus" in res.visual_character.composition
    assert "symmetry" in res.visual_character.composition
    assert res.motifs.state == ResultSectionState.NOT_AVAILABLE  # 0 candidates
    assert any("MOTIF_ANALYSIS_UNAVAILABLE" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_p4_03_vlm_error_isolation(db_session):
    """3. VLM Exception isolation: VLM raises error -> warning added, pipeline completes with Card 1 & 5 intact."""
    settings = Settings(MOTIF_VLM_PROVIDER="REMOTE_OPENAI_COMPATIBLE")
    orchestrator = UnifiedAnalysisOrchestrator(db=db_session, settings=settings)
    raw_bytes = create_dummy_jpeg_bytes()

    with patch("app.domain.orchestrator.service.get_vlm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.analyze = AsyncMock(side_effect=VLMProviderError("VLM connection timed out"))
        mock_get_provider.return_value = mock_provider

        res = await orchestrator.run_analysis(raw_bytes=raw_bytes)

        assert any("MOTIF_ANALYSIS_UNAVAILABLE: VLM connection timed out" in w for w in res.warnings)
        assert res.visual_character.state == ResultSectionState.READY
        assert res.historical_connections.state in (ResultSectionState.READY, ResultSectionState.NOT_AVAILABLE)


@pytest.mark.asyncio
async def test_p4_04_threadpool_offload_spy(db_session):
    """4. Threadpool offload proof: run_in_threadpool is called at least twice per analysis run."""
    settings = Settings(MOTIF_VLM_PROVIDER="DISABLED")
    orchestrator = UnifiedAnalysisOrchestrator(db=db_session, settings=settings)
    raw_bytes = create_dummy_jpeg_bytes()

    from starlette.concurrency import run_in_threadpool as real_threadpool
    with patch("app.domain.orchestrator.service.run_in_threadpool", side_effect=real_threadpool) as mock_threadpool:
        res = await orchestrator.run_analysis(raw_bytes=raw_bytes)

        assert mock_threadpool.call_count >= 2
        assert res.visual_character.state == ResultSectionState.READY
