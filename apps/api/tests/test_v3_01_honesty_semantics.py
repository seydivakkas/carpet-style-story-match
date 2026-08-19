"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Unit tests for Phase P3 Honesty & Semantics Hardening.
Tests:
1. Auto-confirmed vs Curator-confirmed status separation (AUTO_CONFIRMED for conf >= 0.85).
2. Dynamic composition derived from Style DNA 9D dimensions (focal_strength & structural_order).
3. Visual Retrieval distance threshold filtering (NO_MATCH / min_proximity_pct).
"""
import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock, patch

from app.domain.result_experience.schemas import ResultSectionState
from app.domain.result_experience.service import UnifiedUploadResultService
from app.domain.visual_retrieval.service import VisualRetrievalService
from app.domain.visual_retrieval.models import (
    VisualRetrievalQuery,
    QuerySourceType,
    StyleDimensionValue,
)
from app.domain.styledna.engine import StyleDNAEngine


def create_dummy_jpeg_bytes(width: int = 100, height: int = 100, color=(128, 64, 32)) -> bytes:
    """Helper creating valid JPEG bytes."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, encoded_img = cv2.imencode(".jpg", img)
    if not success:
        raise RuntimeError("Failed to encode synthetic JPEG image")
    return encoded_img.tobytes()


def create_medallion_jpeg_bytes() -> bytes:
    """Creates a synthetic image with a strong central medallion (high focal strength)."""
    img = np.full((200, 200, 3), (30, 30, 180), dtype=np.uint8)
    cv2.circle(img, (100, 100), 60, (220, 220, 30), -1)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


def create_repeating_border_jpeg_bytes() -> bytes:
    """Creates a synthetic image with uniform repeating stripes/border."""
    img = np.full((200, 200, 3), (120, 50, 50), dtype=np.uint8)
    for i in range(0, 200, 20):
        cv2.line(img, (i, 0), (i, 200), (40, 180, 40), 4)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


CANONICAL_DIM_KEYS = [
    "color_energy", "color_diversity", "contrast", "warmth",
    "visual_complexity", "structural_order", "rhythm_repetition",
    "focal_strength", "form_language"
]


@pytest.mark.asyncio
async def test_d1_01_auto_confirmed_high_confidence_unlocks_knowledge():
    """1. High confidence motif candidate (conf >= 0.85) gets status AUTO_CONFIRMED."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-90",
                "visual_descriptor": "tree_like",
                "confidence": 0.90,
                "proposed_canonical_motif_key": "tree-of-life",
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
    )

    assert res.motifs.candidates[0].status == "AUTO_CONFIRMED"
    assert res.motifs.review_summary.confirmed_count == 1


@pytest.mark.asyncio
async def test_d1_02_ai_candidate_low_confidence_gated():
    """2. Low confidence candidate (conf < 0.85) gets status AI_CANDIDATE and locks Card 3 & 4."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-80",
                "visual_descriptor": "tree_like",
                "confidence": 0.80,
                "proposed_canonical_motif_key": "tree-of-life",
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
    )

    assert res.motifs.candidates[0].status == "AI_CANDIDATE"
    assert res.motifs.review_summary.confirmed_count == 0
    assert res.motifs.review_summary.pending_count == 1
    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW


@pytest.mark.asyncio
async def test_d2_dynamic_composition_from_style_dna():
    """3. Composition values in Card 1 are derived from D8 (focal_strength) and D6 (structural_order)."""
    raw_img = create_medallion_jpeg_bytes()
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(raw_bytes=raw_img)

    comp = res.visual_character.composition
    dims = res.visual_character.dimensions

    assert "central_focus" in comp
    assert "symmetry" in comp
    assert comp["central_focus"] == dims["focal_strength"]
    assert comp["symmetry"] == dims["structural_order"]


@pytest.mark.asyncio
async def test_d3_01_retrieval_threshold_filters_below():
    """4. VisualRetrievalService filters candidates below min_proximity_pct threshold."""
    query_dna = [StyleDimensionValue(dimension_key=k, value=0.1) for k in CANONICAL_DIM_KEYS]
    query = VisualRetrievalQuery(
        query_id="q-001",
        query_source_type=QuerySourceType.USER_UPLOAD,
        style_dna=query_dna,
    )

    mock_cand = MagicMock()
    mock_cand.historical_reference_id = "hist-001"
    mock_cand.reference_key = "ref-001"
    mock_cand.institution = "Test Museum"
    mock_cand.object_title = "Test Object"
    mock_cand.museum_object_id = "M-001"
    mock_cand.canonical_source_url = None
    mock_cand.primary_image_url = None
    mock_cand.museum_metadata = {}
    mock_cand.metadata_provenance = {}
    mock_cand.vector = {k: 0.9 for k in CANONICAL_DIM_KEYS}  # Very distant vector

    service = VisualRetrievalService(db=None, min_proximity_pct=50.0)
    with patch("app.domain.visual_retrieval.corpus.HistoricalVisualCorpusProvider.load_eligible_corpus_sync", return_value=([mock_cand], MagicMock())):
        matches, _ = service.retrieve_historical_sync(query)
        assert len(matches) == 0


@pytest.mark.asyncio
async def test_d3_02_retrieval_threshold_preserves_above():
    """5. Candidates above threshold are preserved."""
    query_vec = {k: 0.5 for k in CANONICAL_DIM_KEYS}
    query = VisualRetrievalQuery(
        query_id="q-002",
        query_source_type=QuerySourceType.USER_UPLOAD,
        style_dna=query_vec,
    )

    mock_cand = MagicMock()
    mock_cand.historical_reference_id = "hist-002"
    mock_cand.reference_key = "ref-002"
    mock_cand.institution = "Test Museum"
    mock_cand.object_title = "Close Match"
    mock_cand.museum_object_id = "M-002"
    mock_cand.canonical_source_url = None
    mock_cand.primary_image_url = None
    mock_cand.museum_metadata = {}
    mock_cand.metadata_provenance = {}
    mock_cand.vector = dict(query_vec)  # Exact match -> 100% proximity

    service = VisualRetrievalService(db=None, min_proximity_pct=30.0)
    with patch("app.domain.visual_retrieval.corpus.HistoricalVisualCorpusProvider.load_eligible_corpus_sync", return_value=([mock_cand], MagicMock())):
        matches, _ = service.retrieve_historical_sync(query)
        assert len(matches) == 1
        assert matches[0].visual_proximity_score > 30.0


@pytest.mark.asyncio
async def test_d3_03_retrieval_zero_threshold_preserves_legacy_top_k():
    """6. Setting min_proximity_pct to 0.0 returns legacy unconditional top-k results."""
    query_dna = [StyleDimensionValue(dimension_key=k, value=0.1) for k in CANONICAL_DIM_KEYS]
    query = VisualRetrievalQuery(
        query_id="q-003",
        query_source_type=QuerySourceType.USER_UPLOAD,
        style_dna=query_dna,
    )

    mock_cand = MagicMock()
    mock_cand.historical_reference_id = "hist-003"
    mock_cand.reference_key = "ref-003"
    mock_cand.institution = "Test Museum"
    mock_cand.object_title = "Distant Match"
    mock_cand.museum_object_id = "M-003"
    mock_cand.canonical_source_url = None
    mock_cand.primary_image_url = None
    mock_cand.museum_metadata = {}
    mock_cand.metadata_provenance = {}
    mock_cand.vector = {k: 0.9 for k in CANONICAL_DIM_KEYS}

    service = VisualRetrievalService(db=None, min_proximity_pct=0.0)
    with patch("app.domain.visual_retrieval.corpus.HistoricalVisualCorpusProvider.load_eligible_corpus_sync", return_value=([mock_cand], MagicMock())):
        matches, _ = service.retrieve_historical_sync(query)
        assert len(matches) == 1
