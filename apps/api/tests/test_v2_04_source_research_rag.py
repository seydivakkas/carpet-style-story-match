"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Source Research Engine & Evidence RAG Test Suite.
Verifies input gating, neutral queries, source tiers, evidence extraction,
traceability, color safety, and API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

from app.domain.research import (
    ResearchSubject,
    ResearchVerificationStatus,
    ResearchQueryBuilder,
    SourceQualityFilter,
    SourceTier,
    EvidenceRetrievalEngine,
    EvidencePackBuilder,
    SourceResearchService,
    EVIDENCE_PACK_SCHEMA_VERSION,
    RESEARCH_QUERY_PLAN_VERSION
)
from app.domain.research.models import EvidencePack, EvidenceUnit, ResearchSourceDocument


# 1. Unverified Motif Input Gate Test
@pytest.mark.asyncio
async def test_unverified_motif_research_blocked():
    """Unverified candidates (AI_CANDIDATE, UNMAPPED, ABSTAINED) MUST be rejected."""
    subject = ResearchSubject(
        subject_id="subj-ai-1",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.AI_CANDIDATE,
        display_name="Star Candidate",
        created_at="2026-08-17T11:00:00Z"
    )

    service = SourceResearchService()
    with pytest.raises(ValueError) as exc_info:
        await service.execute_research(subject)
    assert "BLOCKED for unverified motif candidates" in str(exc_info.value)


# 2. Verified Motif Research Execution
@pytest.mark.asyncio
async def test_verified_motif_research_success():
    """CURATOR_CONFIRMED motif triggers research query plan and generates EvidencePack."""
    subject = ResearchSubject(
        subject_id="subj-conf-1",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
        display_name="Eight Pointed Star",
        created_at="2026-08-17T11:00:00Z"
    )

    service = SourceResearchService()
    pack = await service.execute_research(subject)

    assert pack.schema_version == EVIDENCE_PACK_SCHEMA_VERSION
    assert pack.subject.canonical_motif_key == "star"
    assert len(pack.query_plan.queries) > 0
    assert len(pack.sources) > 0
    assert len(pack.evidence_units) > 0

    # Ensure no claim or story text present
    pack_dict = pack.model_dump()
    assert "final_claim" not in pack_dict
    assert "story" not in pack_dict
    assert "symbolic_meaning" not in pack_dict


# 3. Source Quality Tier Filtering Tests
def test_source_quality_tier_evaluation():
    # Tier 1 Museum
    t1, _ = SourceQualityFilter.evaluate_source(
        "https://www.metmuseum.org/art/collection/search/451001",
        "The Metropolitan Museum of Art",
        "museum_catalogue"
    )
    assert t1 == SourceTier.TIER_1_PRIMARY_INSTITUTIONAL

    # Tier 2 Academic
    t2, _ = SourceQualityFilter.evaluate_source(
        "https://dergipark.org.tr/article/12345",
        "Ankara University Press",
        "academic_journal"
    )
    assert t2 == SourceTier.TIER_1_PRIMARY_INSTITUTIONAL or t2 == SourceTier.TIER_2_SCHOLARLY

    # Rejected Pinterest
    rej_pin, _ = SourceQualityFilter.evaluate_source(
        "https://www.pinterest.com/pin/123456789",
        "Pinterest User",
        "social_media"
    )
    assert rej_pin == SourceTier.REJECTED_SOURCE

    # Rejected Manufacturer Commercial Site
    rej_merinos, _ = SourceQualityFilter.evaluate_source(
        "https://www.merinos.com.tr/product/123",
        "Merinos Carpet Sales",
        "product_page"
    )
    assert rej_merinos == SourceTier.REJECTED_SOURCE


# 4. Neutral Query Generation Tests (No Culture Injected from Category)
def test_neutral_query_plan_generation():
    subject = ResearchSubject(
        subject_id="subj-star",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.VERIFIED_CANONICAL,
        display_name="Star",
        created_at="2026-08-17T11:00:00Z"
    )

    plan = ResearchQueryBuilder.build_query_plan(subject)
    assert plan.query_plan_version == RESEARCH_QUERY_PLAN_VERSION

    # Check queries are neutral
    for q in plan.queries:
        assert "Seljuk" not in q  # Unverified culture assumption must NOT be injected
        assert "Ottoman" not in q
        assert "Islamic" not in q


# 5. Niche & Tree Safety Invariants
@pytest.mark.asyncio
async def test_tree_and_niche_unverified_safety():
    """Unverified tree_like or niche_like candidates CANNOT trigger cultural research."""
    tree_cand = ResearchSubject(
        subject_id="subj-tree-ai",
        canonical_motif_key="tree_of_life",
        verification_status=ResearchVerificationStatus.AI_CANDIDATE,
        display_name="Tree Candidate",
        created_at="2026-08-17T11:00:00Z"
    )

    service = SourceResearchService()
    with pytest.raises(ValueError):
        await service.execute_research(tree_cand)


# 6. No Final Claim / Story Schema Rejection Test
def test_evidence_pack_rejects_forbidden_fields():
    subject = ResearchSubject(
        subject_id="subj-1",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
        display_name="Star",
        created_at="2026-08-17T11:00:00Z"
    )

    plan = ResearchQueryBuilder.build_query_plan(subject)

    # Creating dict with forbidden field 'story' or 'final_claim'
    bad_dict = {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "research_run_id": "run-bad",
        "subject": subject.model_dump(),
        "query_plan": plan.model_dump(),
        "sources": [],
        "evidence_units": [],
        "contradictions": [],
        "coverage": {},
        "provenance": {},
        "final_claim": "This star means eternity."  # FORBIDDEN!
    }

    with pytest.raises(ValueError) as exc_info:
        EvidencePack.model_validate(bad_dict)
    assert "Forbidden field 'final_claim'" in str(exc_info.value)


# 7. Traceability Locator Validation Test
def test_evidence_unit_requires_locator():
    with pytest.raises(ValueError) as exc_info:
        EvidenceUnit(
            evidence_id="ev-1",
            source_id="src-1",
            subject_motif_key="star",
            locator="",  # Empty locator forbidden!
            supporting_excerpt="Short excerpt text",
            normalized_summary="Summary",
            retrieval_score=0.9,
            source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
            content_hash="abc123hash"
        )
    assert "locator" in str(exc_info.value)


# 8. Contradiction Detection Test
def test_contradiction_detection():
    subject = ResearchSubject(
        subject_id="subj-1",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
        display_name="Star",
        created_at="2026-08-17T11:00:00Z"
    )

    u1 = EvidenceUnit(
        evidence_id="ev-1",
        source_id="src-1",
        subject_motif_key="star",
        locator="page-10",
        supporting_excerpt="Attributed to 15th century Safavid weaving period.",
        normalized_summary="Safavid attribution",
        retrieval_score=0.9,
        source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
        content_hash="hash1"
    )
    u2 = EvidenceUnit(
        evidence_id="ev-2",
        source_id="src-2",
        subject_motif_key="star",
        locator="page-45",
        supporting_excerpt="Attributed to 13th century Seljuk Anatolian period.",
        normalized_summary="Seljuk attribution",
        retrieval_score=0.9,
        source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
        content_hash="hash2"
    )

    conflicts = EvidenceRetrievalEngine._detect_conflicts([u1, u2], subject)
    assert len(conflicts) >= 1
    assert conflicts[0].conflict_type == "CONTRADICTORY_HISTORICAL_ATTRIBUTION"


# 9. API Endpoint Tests
@pytest.mark.asyncio
async def test_api_research_provider_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/research/provider-status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["evidence_pack_version"] == EVIDENCE_PACK_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_api_evidence_pack_verified_subject():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "canonical_motif_key": "star",
            "verification_status": "CURATOR_CONFIRMED"
        }
        res = await ac.post("/api/v1/research/evidence-pack", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["schema_version"] == EVIDENCE_PACK_SCHEMA_VERSION
        assert data["subject"]["canonical_motif_key"] == "star"
        assert len(data["evidence_units"]) > 0


@pytest.mark.asyncio
async def test_api_evidence_pack_unverified_subject_blocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "canonical_motif_key": "star",
            "verification_status": "AI_CANDIDATE"
        }
        res = await ac.post("/api/v1/research/evidence-pack", json=payload)
        assert res.status_code == 400
        assert "BLOCKED for unverified candidates" in res.json()["detail"]


# 10. Color Observation & Extraction Engine Tests
def test_color_observation_extraction_and_dye_unknown():
    import cv2
    import numpy as np
    from app.domain.color_analysis import ColorExtractor, ColorObservation, COLOR_OBSERVATION_SCHEMA_VERSION

    # Generate synthetic 50/50 red and blue image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:50, :, 2] = 200  # Red upper half in BGR
    img[50:, :, 0] = 200  # Blue lower half in BGR

    _, buf = cv2.imencode(".png", img)
    raw_bytes = buf.tobytes()

    extractor = ColorExtractor(min_k=2, max_k=4)
    colors = extractor.extract_colors(raw_bytes, k=2)

    assert len(colors) >= 2
    for c in colors:
        assert c.analysis_version == COLOR_OBSERVATION_SCHEMA_VERSION
        assert c.dye_material == "UNKNOWN"  # MANDATORY INVARIANT
        assert 0.0 <= c.coverage <= 1.0
        assert len(c.rgb) == 3
        assert len(c.hsv) == 3
        assert len(c.lab) == 3
        assert c.perceptual_label != "unresolved"


def test_color_observation_rejects_non_unknown_dye():
    from app.domain.color_analysis import ColorObservation

    with pytest.raises(ValueError) as exc_info:
        ColorObservation(
            color_id="col-1",
            rgb=[200, 0, 0],
            hex="#C80000",
            hsv=[0, 255, 200],
            lab=[50.0, 180.0, 150.0],
            coverage=0.5,
            perceptual_label="warm_red",
            dye_material="madder"  # FORBIDDEN!
        )
    assert "dye_material" in str(exc_info.value) or "Dye material" in str(exc_info.value)


def test_color_observation_rejects_symbolism_fields():
    from app.domain.color_analysis import ColorObservation

    bad_dict = {
        "color_id": "col-1",
        "rgb": [0, 0, 200],
        "hex": "#0000C8",
        "hsv": [120, 255, 200],
        "lab": [50.0, 140.0, 75.0],
        "coverage": 0.5,
        "perceptual_label": "indigo_like",
        "symbolism": "protection"  # FORBIDDEN!
    }

    with pytest.raises(ValueError) as exc_info:
        ColorObservation.model_validate(bad_dict)
    assert "Forbidden color symbolism field 'symbolism'" in str(exc_info.value)


# 11. Carpet Analysis Orchestrator Tests
@pytest.mark.asyncio
async def test_carpet_analysis_orchestrator_pipeline():
    import cv2
    import numpy as np
    from app.domain.orchestrator import CarpetAnalysisOrchestrator

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [100, 150, 200]
    _, buf = cv2.imencode(".jpeg", img)
    raw_bytes = buf.tobytes()

    orchestrator = CarpetAnalysisOrchestrator()
    res = await orchestrator.run_pipeline(
        raw_bytes=raw_bytes,
        mime_type="image/jpeg",
        stages=["visual", "research"],
        verified_subject_motif="star"
    )

    assert res["evidence_pack"]["schema_version"] == EVIDENCE_PACK_SCHEMA_VERSION


# 12. Controlled Canonical Motif & Alias Resolution Tests
def test_canonical_motif_alias_resolution():
    from app.domain.research import resolve_canonical_motif_subject, ResearchVerificationStatus

    # Exact canonical match
    subj1 = resolve_canonical_motif_subject("geometric-star")
    assert subj1.canonical_motif_key == "geometric-star"
    assert subj1.known_source_context["resolution_mechanism"] == "EXACT_CANONICAL_MATCH"

    # Curated alias match
    subj2 = resolve_canonical_motif_subject("star")
    assert subj2.canonical_motif_key == "geometric-star"
    assert subj2.known_source_context["resolution_mechanism"] == "CURATED_ALIAS_REGISTRY"

    # Unknown alias must raise UNKNOWN_MOTIF
    with pytest.raises(ValueError) as exc_info:
        resolve_canonical_motif_subject("magic-star")
    assert "UNKNOWN_MOTIF" in str(exc_info.value)

    # Unverified AI candidate status must be BLOCKED
    with pytest.raises(ValueError) as exc_info:
        resolve_canonical_motif_subject("star", caller_verification_status=ResearchVerificationStatus.AI_CANDIDATE)
    assert "BLOCKED for unverified" in str(exc_info.value)


# 13. SSRF Protection Tests
def test_ssrf_security_safeguards():
    from app.domain.research import SourceQualityFilter, SourceTier

    # Localhost / Loopback rejection
    tier1, reason1 = SourceQualityFilter.evaluate_source("http://localhost:8000/admin", "Local Admin", "web")
    assert tier1 == SourceTier.REJECTED_SOURCE
    assert "SSRF Security Violation" in reason1

    tier2, reason2 = SourceQualityFilter.evaluate_source("http://127.0.0.1/secret", "Local IP", "web")
    assert tier2 == SourceTier.REJECTED_SOURCE
    assert "SSRF Security Violation" in reason2

    # AWS Cloud Metadata rejection
    tier3, reason3 = SourceQualityFilter.evaluate_source("http://169.254.169.254/latest/meta-data/", "Metadata API", "web")
    assert tier3 == SourceTier.REJECTED_SOURCE
    assert "SSRF Security Violation" in reason3
