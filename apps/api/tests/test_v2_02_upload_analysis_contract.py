"""
V2-02 User Upload Analysis Contract & Taxonomy Tests.
"""
import json
import pytest
from pathlib import Path
from pydantic import ValidationError
from httpx import AsyncClient

from app.domain.upload_analysis.schemas import (
    UploadAnalysisResult,
    VisualObservation,
    VisualCategoryResult,
    CompositionEvidence,
    MotifCandidate,
    AnalysisAbstention,
    ModelProvenance,
    RegionEvidence,
    BoundingBox2D,
    Point2D,
    Polygon2D,
    CoordinateSpace,
    SourceKind,
    QualityStatus,
    CanonicalizationStatus,
    ProviderType,
    VisualObservationType,
    MotifCandidateStatus,
    AbstentionReasonCode,
    UPLOAD_ANALYSIS_SCHEMA_VERSION,
)
from app.domain.upload_analysis.visual_categories import (
    CANONICAL_VISUAL_CATEGORIES,
    VISUAL_CATEGORY_TAXONOMY_VERSION,
    VisualCategoryKey,
)
from app.domain.upload_analysis.motif_ontology import (
    MOTIF_ONTOLOGY_DEFINITIONS,
    MOTIF_ONTOLOGY_VERSION,
    CANONICAL_PRODUCTION_MOTIFS,
    VisualCandidateKey,
)
from app.domain.upload_analysis.validation import (
    validate_visual_category_taxonomy,
    validate_motif_ontology,
    validate_all_taxonomies,
)


def get_sample_provenance() -> ModelProvenance:
    return ModelProvenance(
        provider_type=ProviderType.TEST_FIXTURE,
        model_id="test-vision-v1",
        model_version="1.0.0",
        prompt_version="v1.0",
        inference_timestamp="2026-08-16T23:40:00Z"
    )


def test_valid_upload_analysis_result():
    prov = get_sample_provenance()
    res = UploadAnalysisResult(
        analysis_id="an-001",
        image_asset_id="img-001",
        image_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        source_kind=SourceKind.USER_UPLOAD,
        quality_status=QualityStatus.PASS,
        canonicalization_status=CanonicalizationStatus.AVAILABLE,
        visual_category=VisualCategoryResult(
            category_key="central_medallion",
            confidence=0.92,
            evidence_observation_ids=["obs-1"]
        ),
        composition_evidence=CompositionEvidence(
            central_focus=0.88,
            border_dominance=0.35,
            vertical_symmetry=0.95
        ),
        visual_observations=[
            VisualObservation(
                observation_id="obs-1",
                observation_type=VisualObservationType.FOCAL_STRUCTURE,
                confidence=0.95,
                description="Merkezde belirgin madalyon odağı",
                region=RegionEvidence(
                    bounding_box=BoundingBox2D(x_min=0.2, y_min=0.2, x_max=0.8, y_max=0.8)
                )
            )
        ],
        motif_candidates=[
            MotifCandidate(
                candidate_id="mc-1",
                visual_candidate_key="medallion_like",
                proposed_canonical_motif_key="medallion",
                confidence=0.89,
                status=MotifCandidateStatus.AI_CANDIDATE
            )
        ],
        provenance=prov
    )
    assert res.schema_version == UPLOAD_ANALYSIS_SCHEMA_VERSION
    assert res.visual_category.category_key == "central_medallion"
    assert len(res.motif_candidates) == 1


def test_invalid_confidence_range():
    with pytest.raises(ValidationError):
        VisualObservation(
            observation_id="obs-inv",
            observation_type=VisualObservationType.COLOR,
            confidence=1.5,  # Invalid: > 1.0
            description="Invalid confidence"
        )


def test_invalid_bounding_box_coordinates():
    with pytest.raises(ValidationError):
        BoundingBox2D(x_min=0.8, y_min=0.1, x_max=0.2, y_max=0.9)  # Invalid: x_min > x_max


def test_model_cannot_confirm_motifs():
    """Verify AI model cannot directly set status CURATOR_CONFIRMED."""
    with pytest.raises(ValidationError):
        MotifCandidate(
            candidate_id="mc-invalid",
            visual_candidate_key="tree_like",
            proposed_canonical_motif_key="tree-of-life",
            confidence=0.95,
            status=MotifCandidateStatus.CURATOR_CONFIRMED  # Forbidden for model predictions!
        )


def test_rejection_of_forbidden_cultural_fields():
    """Verify strict contract rejects forbidden cultural keys."""
    prov = get_sample_provenance()
    raw = {
        "analysis_id": "an-002",
        "image_asset_id": "img-002",
        "image_sha256": "abc123hash",
        "visual_category": {"category_key": "central_medallion", "confidence": 0.9},
        "composition_evidence": {},
        "provenance": prov.model_dump(),
        "culture": "Seljuk",  # FORBIDDEN!
    }
    with pytest.raises(ValidationError):
        UploadAnalysisResult.model_validate(raw)


def test_niche_safety_invariant():
    """Verify prayer_niche_like remains purely visual without religious labels."""
    cat = next(c for c in CANONICAL_VISUAL_CATEGORIES if c["category_key"] == "prayer_niche_like")
    assert cat["label_tr"] == "Mihrap/Niş Benzeri Kompozisyon"
    assert "namaz halısı" not in cat["label_tr"].lower()
    assert "prayer rug" not in cat["label_en"].lower()


def test_tree_safety_invariant():
    """Verify tree_like candidate remains AI_CANDIDATE needing semantic review."""
    mc = MotifCandidate(
        candidate_id="mc-tree",
        visual_candidate_key="tree_like",
        proposed_canonical_motif_key="tree-of-life",
        confidence=0.85,
        status=MotifCandidateStatus.AI_CANDIDATE
    )
    assert mc.status == MotifCandidateStatus.AI_CANDIDATE
    assert mc.status != MotifCandidateStatus.CURATOR_CONFIRMED


def test_unmapped_motif_candidate_support():
    mc = MotifCandidate(
        candidate_id="mc-unmapped",
        visual_candidate_key="unmapped_visual_motif",
        proposed_canonical_motif_key=None,
        confidence=0.60,
        status=MotifCandidateStatus.UNMAPPED_MOTIF_CANDIDATE
    )
    assert mc.status == MotifCandidateStatus.UNMAPPED_MOTIF_CANDIDATE
    assert mc.proposed_canonical_motif_key is None


def test_cropped_abstention_does_not_create_absence_claim():
    abst = AnalysisAbstention(
        scope="motif_candidate",
        reason_code=AbstentionReasonCode.CROPPED_REGION,
        message="Bordür bölgesi kırpılmış olduğu için tarak biçimi kontrol edilemedi"
    )
    assert abst.reason_code == AbstentionReasonCode.CROPPED_REGION
    assert "absent" not in abst.message.lower()


def test_visual_category_taxonomy_validation():
    val_res = validate_visual_category_taxonomy()
    assert val_res["valid"] is True
    assert val_res["total_categories"] == 11


def test_motif_ontology_validation():
    val_res = validate_motif_ontology()
    assert val_res["valid"] is True
    assert val_res["total_motifs"] == 13


def test_contract_json_serialization_roundtrip():
    prov = get_sample_provenance()
    res = UploadAnalysisResult(
        analysis_id="an-rt",
        image_asset_id="img-rt",
        image_sha256="1234567890abcdef",
        visual_category=VisualCategoryResult(category_key="all_over", confidence=0.88),
        composition_evidence=CompositionEvidence(repetition_strength=0.91),
        provenance=prov
    )
    json_str = res.model_dump_json()
    deserialized = UploadAnalysisResult.model_validate_json(json_str)
    assert deserialized.analysis_id == res.analysis_id
    assert deserialized.visual_category.category_key == "all_over"


def test_json_schema_artifact_validity():
    root = Path(__file__).resolve().parent.parent.parent.parent
    schema_path = root / "data" / "schemas" / "upload-analysis-v1.schema.json"
    assert schema_path.exists()
    content = json.loads(schema_path.read_text(encoding="utf-8"))
    assert content["version"] == "upload-analysis-v1.0.0"


@pytest.mark.asyncio
async def test_taxonomies_api_endpoints(client: AsyncClient):
    """Test read-only taxonomy endpoints."""
    # 1. Visual Categories Endpoint
    res_cat = await client.get("/api/v1/taxonomies/visual-categories")
    assert res_cat.status_code == 200
    data_cat = res_cat.json()
    assert data_cat["taxonomy_version"] == VISUAL_CATEGORY_TAXONOMY_VERSION
    assert data_cat["total_categories"] == 11

    # 2. Motifs Ontology Endpoint
    res_mot = await client.get("/api/v1/taxonomies/motifs")
    assert res_mot.status_code == 200
    data_mot = res_mot.json()
    assert data_mot["ontology_version"] == MOTIF_ONTOLOGY_VERSION
    assert data_mot["total_motifs"] == 13

    # 3. Contract Schema Endpoint
    res_sch = await client.get("/api/v1/upload-analysis/schema")
    assert res_sch.status_code == 200
    data_sch = res_sch.json()
    assert data_sch["schema_version"] == UPLOAD_ANALYSIS_SCHEMA_VERSION
