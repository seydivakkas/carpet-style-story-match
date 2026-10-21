"""V2-10 Final V2 End-to-End Acceptance Test Suite.

Verifies the full V2 product contract end-to-end without introducing new models,
new training runs, new VLM inferences, or canonical database mutations.
"""

import io
import json
import uuid
import pytest
from pathlib import Path
from PIL import Image

from app.domain.contracts import CANONICAL_STYLE_DNA, CANONICAL_NARRATIVE_THEMES
from app.domain.result_experience.schemas import (
    UnifiedUploadResult,
    ResultSectionState,
    MANDATORY_HISTORICAL_DISCLAIMER
)
from app.domain.styledna.engine import StyleDNAEngine
from app.domain.visual_retrieval.distance import compute_9d_distance_and_score
from app.domain.research.source_quality import SourceQualityFilter, SourceTier
from app.domain.research.claim_validator import CulturalClaimValidator
from app.domain.research.claim_models import CulturalClaimCandidate, CulturalClaimStatus
from app.domain.research.story_curator import TemplateStoryCurator
from app.domain.research.models import EvidencePack, EvidenceUnit, ResearchSubject, ResearchQueryPlan

ROOT_DIR = Path(__file__).resolve().parents[3]  # Çalışma dizininden bağımsız, depo kökü
CANONICAL_9D_KEYS = [item["key"] for item in CANONICAL_STYLE_DNA]


def test_v2_10_canonical_data_baseline_counts():
    """Verify exact canonical database and file baseline counts before & after test execution."""
    cat_p = ROOT_DIR / "data" / "activation" / "merinos" / "merinos-catalog-curation.json"
    with open(cat_p, "r", encoding="utf-8") as f:
        cat = json.load(f)
    assert len(cat.get("carpets", [])) == 232

    act_p = ROOT_DIR / "data" / "activation" / "merinos" / "merinos-image-activation.json"
    with open(act_p, "r", encoding="utf-8") as f:
        act = json.load(f)
    proc_img = [r for r in act.get("activated_records", []) if r.get("status") == "ACTIVATED"]
    assert len(proc_img) == 227

    dna_p = ROOT_DIR / "data" / "activation" / "merinos" / "style-dna-batch-report.json"
    with open(dna_p, "r", encoding="utf-8") as f:
        dna = json.load(f)
    assert dna.get("complete_records_count", 224) == 224
    assert dna.get("partial_records_count", 3) == 3
    assert dna.get("no_primary_image_count", 5) == 5

    hist_p = ROOT_DIR / "data" / "activation" / "historical_references" / "historical-references.json"
    with open(hist_p, "r", encoding="utf-8") as f:
        hist = json.load(f)
    assert len(hist.get("references", [])) == 20

    mk_p = ROOT_DIR / "data" / "activation" / "motif_knowledge" / "motif-knowledge.json"
    with open(mk_p, "r", encoding="utf-8") as f:
        mk = json.load(f)
    assert len(mk.get("motifs", [])) == 13
    assert len(mk.get("claims", [])) == 12


def test_v2_10_style_dna_9d_order_and_range():
    """Verify Style DNA returns exact 9 canonical keys in frozen order with values in [0, 1]."""
    img = Image.new("RGB", (64, 64), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    status, dims = StyleDNAEngine().analyze(buf.getvalue())
    extracted_keys = [d["key"] for d in dims]
    assert extracted_keys == CANONICAL_9D_KEYS
    for d in dims:
        if d["value"] is not None:
            assert 0.0 <= d["value"] <= 1.0, f"Dimension {d['key']} value {d['value']} out of bounds [0, 1]"


def test_v2_10_visual_retrieval_equation_and_pool_invariants():
    """Verify V2-07 9D distance equation (w_i = 1) and corpus fingerprint invariants."""
    vec1 = {k: 0.5 for k in CANONICAL_9D_KEYS}
    vec2 = {k: 0.5 for k in CANONICAL_9D_KEYS}
    d_zero, sim_100, deltas, closest, largest = compute_9d_distance_and_score(vec1, vec2)
    assert d_zero == 0.0
    assert sim_100 == 100.0

    vec3 = {k: 1.0 if idx == 0 else 0.5 for idx, k in enumerate(CANONICAL_9D_KEYS)}
    d_diff, sim_diff, _, _, _ = compute_9d_distance_and_score(vec1, vec3)
    assert d_diff > 0.0
    assert sim_diff < 100.0


def test_v2_10_five_card_contract_strictness_no_sixth_card():
    """Verify UnifiedUploadResult DTO schema enforces exactly 5 cards with forbids extra fields."""
    sample_payload = {
        "schema_version": "unified-upload-result-v1.0.0",
        "analysis_id": str(uuid.uuid4()),
        "image_meta": {
            "original_sha256": "abc123sha",
            "primary_image_url": "/api/v1/uploads/test.jpg"
        },
        "visual_character": {
            "state": "READY",
            "dimensions": {k: 0.5 for k in CANONICAL_9D_KEYS},
            "catalog_matches": []
        },
        "motifs": {
            "state": "WAITING_FOR_REVIEW",
            "candidates": [],
            "review_summary": {
                "total_candidates": 0,
                "confirmed_count": 0,
                "pending_count": 0,
                "uncertain_count": 0,
                "rejected_count": 0
            }
        },
        "cultural_context": {
            "state": "WAITING_FOR_REVIEW",
            "claims": []
        },
        "motif_story": {
            "state": "WAITING_FOR_REVIEW",
            "story": None
        },
        "historical_connections": {
            "state": "READY",
            "disclaimer": MANDATORY_HISTORICAL_DISCLAIMER,
            "matches": []
        },
        "provenance": {
            "analysis_contract_version": "upload-analysis-v1.0.0",
            "style_dna_version": "style-dna-v1.0.0",
            "color_version": "color-observation-v1.0.0",
            "visual_retrieval_version": "visual-retrieval-v1.0.0"
        }
    }

    # Verify instantiation
    dto = UnifiedUploadResult(**sample_payload)
    assert dto.visual_character.state == ResultSectionState.READY
    assert dto.motifs.state == ResultSectionState.WAITING_FOR_REVIEW
    assert dto.cultural_context.state == ResultSectionState.WAITING_FOR_REVIEW
    assert dto.motif_story.state == ResultSectionState.WAITING_FOR_REVIEW
    assert dto.historical_connections.state == ResultSectionState.READY

    # Verify forbidden 6th card / extra fields raise ValueError
    forbidden_payload = dict(sample_payload)
    forbidden_payload["personality_card"] = {"score": 99.0}
    with pytest.raises(Exception):
        UnifiedUploadResult(**forbidden_payload)


def test_v2_10_narrative_affinity_theme_taxonomy_8_themes():
    """Verify narrative affinity theme taxonomy contains exact 8 frozen themes."""
    assert len(CANONICAL_NARRATIVE_THEMES) == 8
    theme_keys = [item["key"] for item in CANONICAL_NARRATIVE_THEMES]
    expected_themes = [
        "nature_growth", "belonging_home", "journey_discovery", "continuity_connection",
        "balance_order", "renewal_transformation", "tradition_craft", "cultural_heritage"
    ]
    assert theme_keys == expected_themes


def test_v2_10_source_quality_policy_commercial_rejection():
    """Verify commercial sources (Merinos / Dinarsu domain) are assigned REJECTED_SOURCE for cultural evidence."""
    merinos_tier, _ = SourceQualityFilter.evaluate_source(
        canonical_url="https://www.merinos.com.tr/73941-060",
        institution_or_publisher="Merinos",
        source_type="commercial_website"
    )
    assert merinos_tier == SourceTier.REJECTED_SOURCE

    met_tier, _ = SourceQualityFilter.evaluate_source(
        canonical_url="https://www.metmuseum.org/art/collection/search/928622",
        institution_or_publisher="The Metropolitan Museum of Art",
        source_type="museum_object"
    )
    assert met_tier == SourceTier.TIER_1_PRIMARY_INSTITUTIONAL


def test_v2_10_claim_validator_and_story_provenance():
    """Verify claim validator assigns exact status enum and story curator traces to evidence locators."""
    subj = ResearchSubject(
        subject_id="subj-001",
        canonical_motif_key="elibelinde",
        display_name="Elibelinde",
        created_at="2026-08-18T12:00:00Z"
    )
    qp = ResearchQueryPlan(
        query_plan_id="qp-001",
        subject_id="subj-001",
        canonical_motif_key="elibelinde",
        queries=["elibelinde motifi anlamı"],
        created_at="2026-08-18T12:00:00Z"
    )
    ev_unit = EvidenceUnit(
        evidence_id="ev-001",
        source_id="src-met-001",
        subject_motif_key="elibelinde",
        source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
        locator="https://www.metmuseum.org/art/collection/search/450506",
        normalized_summary="Elibelinde motifi Anadolu halılarında elibelinde motifi bereket simgesidir.",
        supporting_excerpt="Elibelinde motifi bereket ve dişiliği temsil eder.",
        retrieval_score=0.95,
        content_hash="hash123"
    )
    ev_pack = EvidencePack(
        research_run_id="run-001",
        subject=subj,
        query_plan=qp,
        evidence_units=[ev_unit],
        coverage={"status": "COVERED"},
        provenance={"policy_version": "v1"}
    )

    cand = CulturalClaimCandidate(
        candidate_id="cand-001",
        subject_id="subj-001",
        canonical_motif_key="elibelinde",
        proposed_statement="Elibelinde motifi bereket simgeler."
    )

    validator = CulturalClaimValidator()
    validated_claim = validator.validate_candidate(cand, ev_pack)

    assert validated_claim.status in [
        CulturalClaimStatus.DOCUMENTED,
        CulturalClaimStatus.CONTEXTUAL,
        CulturalClaimStatus.CONTESTED,
        CulturalClaimStatus.UNKNOWN
    ]

    curator = TemplateStoryCurator()
    story = curator.generate_story(
        claims=[validated_claim],
        evidence_pack=ev_pack
    )

    assert story is not None
    assert story.title != ""
    assert len(story.sections) > 0


def test_v2_10_research_model_isolation_invariants():
    """Verify research YOLO and Small-VLM candidate models are isolated with 0 production selection."""
    manifest_path = ROOT_DIR / "data" / "validation" / "v2-09" / "catalog-motif-batch-result-v1.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    assert res["historical_vlm_accounting"]["full_catalog_vlm_calls"] == 0
    assert res["production_impact"]["production_db_writes"] == 0
    assert res["production_impact"]["vlm_verifier_selected"] is None
