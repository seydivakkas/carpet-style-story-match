"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Comprehensive Focused Test Suite for V2-08 / V2-08A
Unified 5-Card User Upload Result Experience & Trust Boundary.
"""
import io
import uuid
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
from app.domain.result_experience.schemas import (
    UnifiedUploadResult,
    ResultSectionState,
    MANDATORY_HISTORICAL_DISCLAIMER,
    VisualCharacterCard,
    MotifCard,
    CulturalContextCard,
    MotifStoryCard,
    HistoricalConnectionsCard,
)
from app.domain.result_experience.service import UnifiedUploadResultService
from app.domain.motif_review.schemas import ReviewResultingStatusEnum

client = TestClient(app)


def create_dummy_jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    """Helper to generate valid JPEG image bytes in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_v2_08_result_schema_structure():
    """1. Verify UnifiedUploadResult DTO schema version and 5-card structure."""
    raw_img = create_dummy_jpeg_bytes()
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        analysis_id=uuid.uuid4(),
    )

    assert res.schema_version == "unified-upload-result-v1.0.0"
    assert isinstance(res.visual_character, VisualCharacterCard)
    assert isinstance(res.motifs, MotifCard)
    assert isinstance(res.cultural_context, CulturalContextCard)
    assert isinstance(res.motif_story, MotifStoryCard)
    assert isinstance(res.historical_connections, HistoricalConnectionsCard)


def test_v2_08_extra_fields_forbidden():
    """2. Verify strict extra='forbid' validation on DTOs."""
    with pytest.raises(ValidationError):
        VisualCharacterCard(
            state=ResultSectionState.READY,
            dimensions={},
            palette=[],
            composition={},
            catalog_matches=[],
            forbidden_score=100.0,  # Unexpected field
        )


@pytest.mark.asyncio
async def test_v2_08_catalog_nested_under_card_1():
    """3. Verify catalog visual retrieval is strictly nested under visual_character."""
    raw_img = create_dummy_jpeg_bytes()
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        analysis_id=uuid.uuid4(),
    )

    # Catalog matches must be an attribute of visual_character, not a root-level 6th card
    assert hasattr(res.visual_character, "catalog_matches")
    assert not hasattr(res, "catalog_matches")


@pytest.mark.asyncio
async def test_v2_08_new_upload_gating():
    """4. Verify gating state when motif candidate is unreviewed (WAITING_FOR_REVIEW)."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.85,
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions={},  # Unreviewed -> PENDING
    )

    assert res.visual_character.state == ResultSectionState.READY
    assert res.motifs.state == ResultSectionState.WAITING_FOR_REVIEW
    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert "insan incelemesinden geçmesi gerekiyor" in res.cultural_context.user_message
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW
    assert "insan incelemesinden geçmesi gerekiyor" in res.motif_story.user_message


@pytest.mark.asyncio
async def test_v2_08_high_confidence_gating():
    """5. High AI confidence (0.999) without human review does NOT unlock cultural context."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.999,
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions={},  # No curator review
    )

    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW


@pytest.mark.asyncio
async def test_v2_08_uncertain_review_gating():
    """6. UNCERTAIN review status keeps cultural cards gated."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "hook_like",
                "confidence": 0.75,
            }
        ],
    }

    review_resolutions = {
        "cand-001": ReviewResultingStatusEnum.UNCERTAIN
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions=review_resolutions,
    )

    assert res.motifs.candidates[0].status == "UNCERTAIN"
    assert res.motifs.review_summary.uncertain_count == 1
    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW


@pytest.mark.asyncio
async def test_v2_08_rejected_review_gating():
    """7. REJECTED review status keeps cultural cards gated."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "dragon_like",
                "confidence": 0.70,
            }
        ],
    }

    review_resolutions = {
        "cand-001": ReviewResultingStatusEnum.REJECTED
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions=review_resolutions,
    )

    assert res.motifs.candidates[0].status == "REJECTED"
    assert res.motifs.review_summary.rejected_count == 1
    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW


@pytest.mark.asyncio
async def test_v2_08_confirmed_no_research():
    """8. CURATOR_CONFIRMED without research -> WAITING_FOR_RESEARCH."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.85,
                "confirmed_canonical_motif_key": "tree-of-life",
            }
        ],
    }

    review_resolutions = {
        "cand-001": ReviewResultingStatusEnum.CURATOR_CONFIRMED
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions=review_resolutions,
        precomputed_claim=None,
        precomputed_story=None,
    )

    assert res.motifs.state == ResultSectionState.READY
    assert res.motifs.review_summary.confirmed_count == 1
    assert res.cultural_context.state == ResultSectionState.WAITING_FOR_RESEARCH
    assert "henüz mevcut değil" in res.cultural_context.user_message
    assert res.motif_story.state == ResultSectionState.WAITING_FOR_RESEARCH
    assert "henüz mevcut değil" in res.motif_story.user_message


@pytest.mark.asyncio
async def test_v2_08_full_ready_fixture():
    """9. Confirmed review + research -> All 5 cards READY."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.85,
            }
        ],
    }

    review_resolutions = {
        "cand-001": ReviewResultingStatusEnum.CURATOR_CONFIRMED
    }

    claim = {
        "claim_id": "claim-001",
        "status": "DOCUMENTED",
        "statement_tr": "Hayat ağacı motifi sonsuzluk ve soy devamını simgeler.",
        "sources": [
            {
                "institution": "Metropolitan Museum of Art",
                "title": "Oriental Rugs Collection",
                "locator": "Cat No. 14",
            }
        ],
    }

    story = {
        "title": "Hayat Ağacı Anlatısı",
        "summary": "Köklü gelenek ve doğa sevgisi.",
        "sections": [
            {
                "heading": "Köken",
                "content": "Anadolu dokumalarında sıkça rastlanır.",
                "citations": ["MMA-2024-C001"],
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions=review_resolutions,
        precomputed_claim=claim,
        precomputed_story=story,
    )

    assert res.visual_character.state == ResultSectionState.READY
    assert res.motifs.state == ResultSectionState.READY
    assert res.cultural_context.state == ResultSectionState.READY
    assert res.motif_story.state == ResultSectionState.READY
    assert res.historical_connections.state in (ResultSectionState.READY, ResultSectionState.NOT_AVAILABLE)


@pytest.mark.asyncio
async def test_v2_08_contested_claim_flagged():
    """10. CONTESTED claim is preserved and marked."""
    raw_img = create_dummy_jpeg_bytes()
    claim = {
        "claim_id": "claim-002",
        "status": "CONTESTED",
        "statement_tr": "Ejder motifinin kökeni hakkında farklı kaynaklar çelişmektedir.",
        "sources": [
            {"institution": "V&A Museum", "title": "Carpet Studies", "locator": "p. 50"}
        ],
    }
    story = {
        "title": "Ejder Motifi Anlatısı",
        "summary": "Mitolojik sembolizm.",
        "sections": [
            {
                "heading": "Köken Tartışması",
                "content": "Asya ile Anadolu etkileşimi tartışmalıdır.",
                "citations": ["VA-2024"],
                "is_contested": True,
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "dragon_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_claim=claim,
        precomputed_story=story,
    )

    assert res.cultural_context.claims[0].status == "CONTESTED"
    assert res.motif_story.story.sections[0].is_contested is True


@pytest.mark.asyncio
async def test_v2_08_unknown_claim_preserved():
    """11. UNKNOWN claim is preserved and not omitted or fabricated."""
    raw_img = create_dummy_jpeg_bytes()
    claim = {
        "claim_id": "claim-003",
        "status": "UNKNOWN",
        "statement_tr": "Gizemli çengel motifi için yeterli kaynak bulunamadı.",
        "sources": [],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "hook_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_claim=claim,
    )

    assert res.cultural_context.claims[0].status == "UNKNOWN"


@pytest.mark.asyncio
async def test_v2_08_claim_traceability():
    """12. Claim sources retain valid institutional locators."""
    raw_img = create_dummy_jpeg_bytes()
    claim = {
        "claim_id": "claim-004",
        "status": "DOCUMENTED",
        "statement_tr": "Koçboynuzu motifi güç ve bereket simgesidir.",
        "sources": [
            {
                "institution": "Metropolitan Museum of Art",
                "title": "Turkish Carpets",
                "locator": "Page 45, Plate II",
                "canonical_url": "https://www.metmuseum.org/art/collection/search/123",
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "ram_horn_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_claim=claim,
    )

    src = res.cultural_context.claims[0].sources[0]
    assert src.institution == "Metropolitan Museum of Art"
    assert src.locator == "Page 45, Plate II"
    assert src.canonical_url.startswith("https://")


@pytest.mark.asyncio
async def test_v2_08_story_traceability():
    """13. Story sections retain valid citations."""
    raw_img = create_dummy_jpeg_bytes()
    story = {
        "title": "Koçboynuzu Hikâyesi",
        "summary": "Güç ve koruma.",
        "sections": [
            {
                "heading": "Tarihçe",
                "content": "Yörük dokumalarında yaygındır.",
                "citations": ["MMA-2024-C002"],
            }
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "ram_horn_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_story=story,
    )

    assert "MMA-2024-C002" in res.motif_story.story.sections[0].citations


@pytest.mark.asyncio
async def test_v2_08_color_safety_regression():
    """14. Color observations do NOT infer cultural symbolism or dye materials."""
    raw_img = create_dummy_jpeg_bytes()
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        analysis_id=uuid.uuid4(),
    )

    # Check palette items
    for item in res.visual_character.palette:
        item_dict = item.model_dump()
        assert "symbolism" not in item_dict
        assert "meaning" not in item_dict
        assert "dye_material" not in item_dict


@pytest.mark.asyncio
async def test_v2_08_unreviewed_motif_wording_semantics():
    """15. Unreviewed visual candidate keys use strictly visual Turkish labels."""
    raw_img = create_dummy_jpeg_bytes()
    vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {"candidate_id": "c1", "visual_descriptor": "tree_like"},
            {"candidate_id": "c2", "visual_descriptor": "niche_like"},
        ],
    }

    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis=vlm_proposal,
        review_resolutions={},
    )

    assert res.motifs.candidates[0].turkish_label == "Ağaç benzeri biçim"
    assert res.motifs.candidates[1].turkish_label == "Niş benzeri biçim"


def test_v2_08_historical_disclaimer_presence():
    """16. Historical connections card contains exact mandatory disclaimer."""
    card5 = HistoricalConnectionsCard(
        state=ResultSectionState.READY,
        matches=[],
    )
    assert card5.disclaimer == MANDATORY_HISTORICAL_DISCLAIMER


def test_v2_08_no_internal_reviewer_fields_leak():
    """17. Assert no internal reviewer identifiers are exposed in UnifiedUploadResult DTO."""
    res_dict = UnifiedUploadResult(
        schema_version="unified-upload-result-v1.0.0",
        analysis_id=uuid.uuid4(),
        image_meta={
            "original_sha256": "abc",
            "primary_image_url": "/img",
        },
        visual_character={"state": ResultSectionState.READY, "dimensions": {}, "palette": [], "composition": {}, "catalog_matches": []},
        motifs={"state": ResultSectionState.NOT_AVAILABLE, "candidates": [], "review_summary": {"total_candidates": 0, "confirmed_count": 0, "pending_count": 0, "uncertain_count": 0, "rejected_count": 0}},
        cultural_context={"state": ResultSectionState.NOT_AVAILABLE, "claims": []},
        motif_story={"state": ResultSectionState.NOT_AVAILABLE},
        historical_connections={"state": ResultSectionState.NOT_AVAILABLE, "matches": []},
        provenance={"analysis_contract_version": "v1", "style_dna_version": "v1", "visual_retrieval_version": "v1"},
        warnings=[],
    ).model_dump()

    forbidden_internal = [
        "reviewer_ref",
        "reviewer_boundary",
        "review_note",
        "idempotency_key",
        "candidate_snapshot_hash"
    ]
    for key in forbidden_internal:
        assert key not in res_dict


def test_v2_08_client_forged_state_rejection():
    """18. Posting JSON with forged claims/scores to /unified-result fails with 422."""
    forged_payload = {
        "overall_score": 99,
        "review_status": "CURATOR_CONFIRMED",
        "claims": [{"claim_id": "forged-1", "statement_tr": "Forged claim"}],
        "story": {"title": "Forged story"},
    }
    res = client.post(
        "/api/v1/upload-analysis/unified-result",
        json=forged_payload,
    )
    # Must fail because endpoint expects multipart file
    assert res.status_code in (422, 400)


def test_v2_08_zero_model_on_get():
    """19. GET /unified-result executes 0 VLM / AI model inferences."""
    aid = str(uuid.uuid4())
    with patch("app.domain.upload_analysis.service.analyze_user_upload_image") as mock_vlm:
        res = client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
        assert res.status_code == 200
        mock_vlm.assert_not_called()


def test_v2_08_zero_research_network_on_get():
    """20. GET /unified-result executes 0 external research network calls."""
    aid = str(uuid.uuid4())
    with patch("httpx.AsyncClient.get") as mock_http:
        res = client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
        assert res.status_code == 200
        mock_http.assert_not_called()


@pytest.mark.asyncio
async def test_v2_08_zero_db_mutation_on_get():
    """21. GET /unified-result causes zero database mutations."""
    aid = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        subjs_before = (await session.execute(select(func.count(MotifReviewSubjectModel.id)))).scalar()
        events_before = (await session.execute(select(func.count(MotifReviewEventModel.id)))).scalar()
        carpets_before = (await session.execute(select(func.count(CarpetModel.id)))).scalar()
        hist_before = (await session.execute(select(func.count(HistoricalReferenceMetadataModel.id)))).scalar()

    # Make GET request
    res = client.get(f"/api/v1/upload-analysis/{aid}/unified-result")
    assert res.status_code == 200

    async with AsyncSessionLocal() as session:
        subjs_after = (await session.execute(select(func.count(MotifReviewSubjectModel.id)))).scalar()
        events_after = (await session.execute(select(func.count(MotifReviewEventModel.id)))).scalar()
        carpets_after = (await session.execute(select(func.count(CarpetModel.id)))).scalar()
        hist_after = (await session.execute(select(func.count(HistoricalReferenceMetadataModel.id)))).scalar()

    assert subjs_before == subjs_after
    assert events_before == events_after
    assert carpets_before == carpets_after
    assert hist_before == hist_after


@pytest.mark.asyncio
async def test_v2_08_quality_blocked_state():
    """22. Corrupted image bytes return BLOCKED_BY_QUALITY state across all cards."""
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=b"CORRUPTED_NON_IMAGE_BYTES",
        analysis_id=uuid.uuid4(),
    )

    assert res.visual_character.state == ResultSectionState.BLOCKED_BY_QUALITY
    assert res.motifs.state == ResultSectionState.BLOCKED_BY_QUALITY
    assert res.cultural_context.state == ResultSectionState.BLOCKED_BY_QUALITY
    assert res.motif_story.state == ResultSectionState.BLOCKED_BY_QUALITY
    assert res.historical_connections.state == ResultSectionState.BLOCKED_BY_QUALITY


def test_v2_08_no_composite_score():
    """23. Strict prohibition of overall_score, authenticity_score, personality_type."""
    res_dict = UnifiedUploadResult(
        schema_version="unified-upload-result-v1.0.0",
        analysis_id=uuid.uuid4(),
        image_meta={
            "original_sha256": "abc",
            "primary_image_url": "/img",
        },
        visual_character={"state": ResultSectionState.READY, "dimensions": {}, "palette": [], "composition": {}, "catalog_matches": []},
        motifs={"state": ResultSectionState.NOT_AVAILABLE, "candidates": [], "review_summary": {"total_candidates": 0, "confirmed_count": 0, "pending_count": 0, "uncertain_count": 0, "rejected_count": 0}},
        cultural_context={"state": ResultSectionState.NOT_AVAILABLE, "claims": []},
        motif_story={"state": ResultSectionState.NOT_AVAILABLE},
        historical_connections={"state": ResultSectionState.NOT_AVAILABLE, "matches": []},
        provenance={"analysis_contract_version": "v1", "style_dna_version": "v1", "visual_retrieval_version": "v1"},
        warnings=[],
    ).model_dump()

    forbidden = ["overall_score", "authenticity_score", "cultural_score", "personality_type", "match_percentage"]
    for key in forbidden:
        assert key not in res_dict


def test_v2_08_api_endpoint_post_upload():
    """24. POST /unified-result accepts valid image file and returns 5-card result."""
    img_bytes = create_dummy_jpeg_bytes()
    res = client.post(
        "/api/v1/upload-analysis/unified-result",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "unified-upload-result-v1.0.0"
    assert data["visual_character"]["state"] == "READY"
    assert len(data["visual_character"]["dimensions"]) == 9


def test_v2_08_catalog_semantics_visual_only():
    """25. Catalog matches have visual_proximity_score and no recommendation labels."""
    raw_img = create_dummy_jpeg_bytes()
    service = UnifiedUploadResultService(db=None)
    card1 = VisualCharacterCard(
        state=ResultSectionState.READY,
        dimensions={"complexity": 0.5},
        palette=[],
        composition={},
        catalog_matches=[
            {
                "rank": 1,
                "catalog_id": "c-1",
                "sku": "MER-VAL-01",
                "brand": "Merinos",
                "collection": "Vali",
                "product_name": "Vali Klasik",
                "visual_proximity_score": 0.92,
            }
        ],
    )
    match_dict = card1.catalog_matches[0].model_dump()
    assert "visual_proximity_score" in match_dict
    assert "recommended" not in match_dict
    assert "match_percentage" not in match_dict
    assert "best_seller" not in match_dict


def test_v2_08_historical_semantics_visual_only():
    """26. Historical matches have visual_proximity_score and no origin/period inference."""
    card5 = HistoricalConnectionsCard(
        state=ResultSectionState.READY,
        matches=[
            {
                "rank": 1,
                "historical_reference_id": "hist-1",
                "reference_key": "HIST-001",
                "institution": "Metropolitan Museum of Art",
                "object_title": "Ushak Carpet",
                "museum_object_id": "1908.12",
                "date_or_period": "16th century",
                "origin_culture": "Ottoman",
                "visual_proximity_score": 0.88,
            }
        ],
    )
    match_dict = card5.matches[0].model_dump()
    assert "visual_proximity_score" in match_dict
    assert "provenance_score" not in match_dict
    assert "period_match_score" not in match_dict
    assert "origin_match_score" not in match_dict


def test_v2_08_canonical_narrative_themes_count_and_keys():
    """27. Narrative theme registry has exactly 8 frozen canonical themes."""
    from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
    assert len(CANONICAL_NARRATIVE_THEMES) == 8
    expected_keys = [
        "nature_growth",
        "belonging_home",
        "journey_discovery",
        "continuity_connection",
        "balance_order",
        "renewal_transformation",
        "tradition_craft",
        "cultural_heritage",
    ]
    actual_keys = [t["key"] for t in CANONICAL_NARRATIVE_THEMES]
    assert actual_keys == expected_keys


@pytest.mark.asyncio
async def test_v2_08_thematic_affinity_optional_and_absent_by_default():
    """28. Card 4 thematic affinity is optional and absent by default."""
    raw_img = create_dummy_jpeg_bytes()
    story = {
        "title": "Hayat Ağacı Hikâyesi",
        "summary": "Köklü gelenek.",
        "sections": [
            {"heading": "Tarihçe", "content": "Metin", "citations": ["SRC-1"]}
        ],
    }
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "tree_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_story=story,
        precomputed_thematic_affinity=None,  # Absent by default
    )
    assert res.motif_story.thematic_affinity is None


@pytest.mark.asyncio
async def test_v2_08_thematic_affinity_populated_when_provided():
    """29. Card 4 thematic affinity is displayed when valid precomputed affinity is supplied."""
    raw_img = create_dummy_jpeg_bytes()
    story = {
        "title": "Hayat Ağacı Hikâyesi",
        "summary": "Köklü gelenek.",
        "sections": [
            {"heading": "Tarihçe", "content": "Metin", "citations": ["SRC-1"]}
        ],
    }
    affinity_data = {
        "matched_themes": ["nature_growth", "tradition_craft"],
        "affinity_description": "Doğa ve zanaat temalarıyla uyumlu.",
    }
    service = UnifiedUploadResultService(db=None)
    res = await service.assemble_result_from_bytes(
        raw_bytes=raw_img,
        precomputed_vlm_analysis={"candidates": [{"candidate_id": "cand-1", "visual_descriptor": "tree_like"}]},
        review_resolutions={"cand-1": ReviewResultingStatusEnum.CURATOR_CONFIRMED},
        precomputed_story=story,
        precomputed_thematic_affinity=affinity_data,
    )
    assert res.motif_story.thematic_affinity is not None
    assert res.motif_story.thematic_affinity.matched_themes == ["nature_growth", "tradition_craft"]
