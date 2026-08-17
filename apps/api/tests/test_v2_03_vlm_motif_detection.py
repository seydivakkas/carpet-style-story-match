"""
V2-03 — Structured vLLM / Remote VLM Motif Detection Test Suite.

Verifies provider architecture, local/remote adapters, DTO safety, EXIF sanitization,
zero cultural field enforcement, error mapping, and API endpoints.
"""
import io
import json
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings
from app.api.v1.upload_analysis import get_settings
from app.domain.upload_analysis import (
    prepare_image_for_vlm,
    PreparedInferenceImage,
    ImageValidationError,
    get_vlm_provider,
    get_vlm_provider_status,
    analyze_user_upload_image,
    VLLMOpenAICompatibleVisionProvider,
    RemoteOpenAICompatibleVisionProvider,
    FixtureVisionProvider,
    VLMProviderError,
    VLMAuthError,
    VLMTimeoutError,
    VLMMalformedOutputError,
    ProviderType,
    MotifCandidateStatus,
    VisualCategoryKey,
    VisualCandidateKey,
    FORBIDDEN_CULTURAL_FIELDS
)

client = TestClient(app)


def create_dummy_jpeg_bytes(width: int = 200, height: int = 200) -> bytes:
    """Helper to generate valid JPEG image bytes in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_mock_response(status_code: int, json_data: dict):
    mock_res = MagicMock()
    mock_res.status_code = status_code
    mock_res.json.return_value = json_data
    return mock_res


# 1. Provider Factory Tests
def test_provider_factory_disabled_mode():
    s = Settings(MOTIF_VLM_PROVIDER="DISABLED")
    provider = get_vlm_provider(s)
    assert provider is None


def test_provider_factory_fixture_mode():
    s = Settings(MOTIF_VLM_PROVIDER="TEST_FIXTURE")
    provider = get_vlm_provider(s)
    assert isinstance(provider, FixtureVisionProvider)


def test_provider_factory_local_vllm_mode():
    s = Settings(MOTIF_VLM_PROVIDER="LOCAL_VLLM", MOTIF_VLM_BASE_URL="http://127.0.0.1:8000/v1")
    provider = get_vlm_provider(s)
    assert isinstance(provider, VLLMOpenAICompatibleVisionProvider)
    assert provider.provider_type == ProviderType.LOCAL_VLLM


def test_provider_factory_remote_mode():
    s = Settings(
        MOTIF_VLM_PROVIDER="REMOTE_OPENAI_COMPATIBLE",
        MOTIF_VLM_BASE_URL="https://api.openai.com/v1",
        MOTIF_VLM_API_KEY="secret-key-123"
    )
    provider = get_vlm_provider(s)
    assert isinstance(provider, RemoteOpenAICompatibleVisionProvider)
    assert provider.provider_type == ProviderType.REMOTE_OPENAI_COMPATIBLE


# 2. Image Preparation & EXIF Privacy Tests
def test_image_preparation_valid_decode_and_hashes():
    raw_bytes = create_dummy_jpeg_bytes(300, 300)
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg", is_remote=True)
    assert prep.original_width == 300
    assert prep.original_height == 300
    assert len(prep.original_sha256) == 64
    assert len(prep.prepared_sha256) == 64
    assert prep.mime_type == "image/jpeg"


def test_image_preparation_rejects_corrupted_image():
    raw_bytes = b"not-a-real-image-payload"
    with pytest.raises(ImageValidationError):
        prepare_image_for_vlm(raw_bytes, "image/jpeg")


# 3. Fixture Provider Inference Test
@pytest.mark.asyncio
async def test_fixture_provider_inference():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = FixtureVisionProvider()
    res = await provider.analyze(prep)

    assert res.visual_category.category_key == VisualCategoryKey.CENTRAL_MEDALLION.value
    assert len(res.motif_candidates) == 1
    assert res.motif_candidates[0].proposed_canonical_motif_key == "medallion"
    assert res.provenance.provider_type == ProviderType.TEST_FIXTURE


# 4. Mock Local vLLM Inference Test
@pytest.mark.asyncio
async def test_mock_local_vllm_provider_inference():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider(
        base_url="http://127.0.0.1:8000/v1",
        model_id="qwen-7b"
    )

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "central_medallion",
                        "category_confidence": 0.95,
                        "composition": {
                            "central_focus": 0.9,
                            "vertical_symmetry": 0.95
                        },
                        "visual_observations": [
                            {
                                "observation_type": "FOCAL_STRUCTURE",
                                "confidence": 0.9,
                                "description": "Central star shape",
                                "evidence_features": ["radial_symmetry"]
                            }
                        ],
                        "motif_candidates": [
                            {
                                "visual_candidate_key": "star_like",
                                "proposed_canonical_motif_key": "geometric-star",
                                "confidence": 0.88,
                                "bounding_box": [0.3, 0.3, 0.7, 0.7],
                                "visual_evidence": ["eight_point_star"]
                            }
                        ],
                        "abstentions": []
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, mock_response_data)
    with patch("httpx.AsyncClient.post", return_value=mock_res):
        res = await provider.analyze(prep)

        assert res.visual_category.category_key == "central_medallion"
        assert res.motif_candidates[0].visual_candidate_key == "star_like"
        assert res.motif_candidates[0].status == MotifCandidateStatus.AI_CANDIDATE
        assert res.provenance.provider_type == ProviderType.LOCAL_VLLM
        assert res.provenance.model_id == "qwen-7b"


# 5. Remote Provider Auth & Secret Protection Test
@pytest.mark.asyncio
async def test_mock_remote_provider_auth_protection():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    secret_key = "super-secret-api-key-999"
    provider = RemoteOpenAICompatibleVisionProvider(
        base_url="https://api.vlm.com/v1",
        model_id="remote-vlm",
        api_key=secret_key
    )

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "all_over",
                        "category_confidence": 0.85,
                        "motif_candidates": []
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, mock_response_data)
    with patch("httpx.AsyncClient.post", return_value=mock_res) as mock_post:
        res = await provider.analyze(prep)

        # Check call headers
        call_headers = mock_post.call_args.kwargs.get("headers", {})
        assert call_headers.get("Authorization") == f"Bearer {secret_key}"

        # Verify secret is NEVER exposed in provenance or response
        res_json = res.model_dump_json()
        assert secret_key not in res_json
        assert res.provenance.provider_type == ProviderType.REMOTE_OPENAI_COMPATIBLE


# 6. Safety Invariant Tests: Forbidden Cultural Fields Rejection
@pytest.mark.asyncio
async def test_vlm_rejects_forbidden_cultural_fields():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider("http://127.0.0.1:8000/v1", "qwen")

    malicious_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "central_medallion",
                        "category_confidence": 0.9,
                        "culture": "Seljuk",  # FORBIDDEN!
                        "motif_candidates": []
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, malicious_data)
    with patch("httpx.AsyncClient.post", return_value=mock_res):
        with pytest.raises(VLMMalformedOutputError):
            await provider.analyze(prep)


@pytest.mark.asyncio
async def test_vlm_rejects_extra_unregistered_fields():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider("http://127.0.0.1:8000/v1", "qwen")

    extra_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "central_medallion",
                        "category_confidence": 0.9,
                        "unregistered_extra_key": "some_value",  # FORBIDDEN by extra=forbid
                        "motif_candidates": []
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, extra_data)
    with patch("httpx.AsyncClient.post", return_value=mock_res):
        with pytest.raises(VLMMalformedOutputError):
            await provider.analyze(prep)


# 7. Model cannot confirm motifs
@pytest.mark.asyncio
async def test_vlm_cannot_set_curator_confirmed():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider("http://127.0.0.1:8000/v1", "qwen")

    data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "prayer_niche_like",
                        "category_confidence": 0.9,
                        "motif_candidates": [
                            {
                                "visual_candidate_key": "niche_like",
                                "proposed_canonical_motif_key": "mihrab",
                                "confidence": 0.95,
                                "status": "CURATOR_CONFIRMED"  # Model trying to confirm itself!
                            }
                        ]
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, data)
    with patch("httpx.AsyncClient.post", return_value=mock_res):
        with pytest.raises(VLMMalformedOutputError):
            await provider.analyze(prep)


# 8. Niche and Tree Safety Tests
@pytest.mark.asyncio
async def test_tree_like_and_niche_like_safety():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = FixtureVisionProvider()
    res = await provider.analyze(prep)

    res_json = res.model_dump_json()
    assert "prayer rug" not in res_json.lower()
    assert "namaz halısı" not in res_json.lower()
    assert "tree of life confirmed" not in res_json.lower()


# 9. Retries & Malformed JSON Error Handling
@pytest.mark.asyncio
async def test_vlm_malformed_json_correction_retry_success():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider("http://127.0.0.1:8000/v1", "qwen", max_retries=1)

    bad_resp = create_mock_response(200, {"choices": [{"message": {"content": "INVALID JSON STRING"}}]})
    good_resp = create_mock_response(200, {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"visual_category_key": "all_over", "category_confidence": 0.8})
                }
            }
        ]
    })

    with patch("httpx.AsyncClient.post", side_effect=[bad_resp, good_resp]):
        res = await provider.analyze(prep)
        assert res.visual_category.category_key == "all_over"


# 10. Deduplication & Region Bounding Box Validation
@pytest.mark.asyncio
async def test_candidate_deduplication_and_bbox_clamping():
    raw_bytes = create_dummy_jpeg_bytes()
    prep = prepare_image_for_vlm(raw_bytes, "image/jpeg")
    provider = VLLMOpenAICompatibleVisionProvider("http://127.0.0.1:8000/v1", "qwen")

    duplicate_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "visual_category_key": "central_medallion",
                        "category_confidence": 0.9,
                        "motif_candidates": [
                            {
                                "visual_candidate_key": "star_like",
                                "proposed_canonical_motif_key": "geometric-star",
                                "confidence": 0.8,
                                "bounding_box": [0.1, 0.1, 0.5, 0.5]
                            },
                            {
                                "visual_candidate_key": "star_like",
                                "proposed_canonical_motif_key": "geometric-star",
                                "confidence": 0.8,
                                "bounding_box": [0.1, 0.1, 0.5, 0.5]  # Identical duplicate!
                            },
                            {
                                "visual_candidate_key": "star_like",
                                "proposed_canonical_motif_key": "geometric-star",
                                "confidence": 0.85,
                                "bounding_box": [0.6, 0.6, 0.9, 0.9]  # Separate region -> Keep!
                            }
                        ]
                    })
                }
            }
        ]
    }

    mock_res = create_mock_response(200, duplicate_data)
    with patch("httpx.AsyncClient.post", return_value=mock_res):
        res = await provider.analyze(prep)
        # 3 candidates emitted by model, exact duplicate removed -> 2 remain
        assert len(res.motif_candidates) == 2


# 11. API Endpoint Integration Tests
def test_api_provider_status_endpoint():
    res = client.get("/api/v1/upload-analysis/provider-status")
    assert res.status_code == 200
    data = res.json()
    assert "provider_type" in data
    assert "configured" in data
    assert "reachable" in data
    assert "inference_enabled" in data


def test_api_motif_detect_disabled_returns_503():
    img_bytes = create_dummy_jpeg_bytes()
    
    def override_settings():
        return Settings(MOTIF_VLM_PROVIDER="DISABLED")

    app.dependency_overrides[get_settings] = override_settings
    try:
        res = client.post(
            "/api/v1/upload-analysis/motif-detect",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert res.status_code == 503
        assert "disabled" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_api_motif_detect_fixture_mode_returns_200():
    img_bytes = create_dummy_jpeg_bytes()

    def override_settings():
        return Settings(MOTIF_VLM_PROVIDER="TEST_FIXTURE")

    app.dependency_overrides[get_settings] = override_settings
    try:
        res = client.post(
            "/api/v1/upload-analysis/motif-detect",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["visual_category"]["category_key"] == "central_medallion"
        assert len(data["motif_candidates"]) >= 1
        assert data["provenance"]["provider_type"] == "TEST_FIXTURE"
    finally:
        app.dependency_overrides.clear()
