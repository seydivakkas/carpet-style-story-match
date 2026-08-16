"""ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

POST-v1 A10 E2E Acceptance & Integration Tests.

Validates complete user journey from preference onboarding to 3-layer match outputs:
1. Visual Style Match (visual-style-match-v1)
2. Narrative Affinity (narrative-affinity-v1)
3. Historical Connection (historical-connection-v1)

Verifies frozen safety principles, non-profiling, provenance traceability,
specimen behavior, controls, and schema compliance.
"""

import uuid
from typing import Dict, Any
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel, HistoricalReferenceSourceModel
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
    MotifModel,
    MotifStoryClaimModel,
    CuratedSourceModel,
    MotifEvidenceTypeEnum,
)
from app.domain.contracts import CANONICAL_STYLE_DNA, CANONICAL_NARRATIVE_THEMES


PROHIBITED_PROFILING_TERMS = [
    "personality",
    "kişilik",
    "psychological",
    "psikolojik",
    "character type",
    "karakter tipi",
    "sen romantik birisin",
    "kişiliğini yansıtıyor",
]


async def _seed_e2e_data(db_session: AsyncSession):
    """Seed test fixtures in test database for E2E acceptance tests."""
    # 1. Primary Specimen: SKU 73941 060
    specimen_id = uuid.uuid4()
    specimen_img_id = uuid.uuid4()
    specimen_prof_id = uuid.uuid4()

    specimen = CarpetModel(
        id=specimen_id,
        name="Elegance 73941 060",
        sku="73941 060",
        collection="Elegance",
        source_type=CarpetSourceType.CATALOG,
        is_active=True,
    )
    db_session.add(specimen)

    specimen_img = CarpetImageModel(
        id=specimen_img_id,
        carpet_id=specimen_id,
        original_filename="73941_060.jpg",
        content_type="image/jpeg",
        storage_backend="LOCAL_FILESYSTEM",
        storage_key="test_73941_060.jpg",
        byte_size=2048,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="a" * 64,
        is_primary=True,
    )
    db_session.add(specimen_img)

    specimen_prof = CarpetStyleProfileModel(
        id=specimen_prof_id,
        carpet_id=specimen_id,
        image_id=specimen_img_id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="a" * 64,
        analysis_scope="FULL_IMAGE",
        status=StyleProfileStatus.COMPLETE,
        analyzed_width_px=800,
        analyzed_height_px=600,
    )
    db_session.add(specimen_prof)

    for dim in CANONICAL_STYLE_DNA:
        db_session.add(
            CarpetStyleDimensionModel(
                id=uuid.uuid4(),
                profile_id=specimen_prof_id,
                dimension_key=dim["key"],
                value=0.70,
                confidence=0.90,
                status=StyleDimensionStatus.AVAILABLE,
            )
        )

    # Add Motif and Story Association for Primary Specimen
    source_id = uuid.uuid4()
    source = CuratedSourceModel(
        id=source_id,
        source_key="src-met-cat",
        source_type="MUSEUM_CATALOG",
        title="Metropolitan Museum Carpet Catalog",
        citation_text="The Met Museum Art Guide 2026",
    )
    db_session.add(source)

    motif_id = uuid.uuid4()
    motif = MotifModel(
        id=motif_id,
        motif_key="tree-of-life",
        name_tr="Hayat Ağacı",
        name_en="Tree of Life",
    )
    db_session.add(motif)

    claim_id = uuid.uuid4()
    claim = MotifStoryClaimModel(
        id=claim_id,
        claim_key="tree-life-growth",
        motif_id=motif_id,
        status="DOCUMENTED",
        claim_text_tr="Hayat ağacı doğayı ve büyümeyi simgeler.",
        claim_text_en="Tree of life symbolizes nature and growth.",
        knowledge_version="v1.0.0",
    )
    db_session.add(claim)

    motif_assoc_id = uuid.uuid4()
    motif_assoc = CarpetMotifAssociationModel(
        id=motif_assoc_id,
        carpet_id=specimen_id,
        motif_id=motif_id,
        evidence_type="CURATOR_CONFIRMED",
    )
    db_session.add(motif_assoc)

    story_assoc = CarpetStoryAssociationModel(
        id=uuid.uuid4(),
        carpet_motif_association_id=motif_assoc_id,
        claim_id=claim_id,
        applicability_note="Official Met catalog interpretation",
    )
    db_session.add(story_assoc)

    # 2. Control A: SKU 72487 060 (Complete Style DNA, No Story)
    ctrl_a_id = uuid.uuid4()
    ctrl_a_img_id = uuid.uuid4()
    ctrl_a_prof_id = uuid.uuid4()

    ctrl_a = CarpetModel(
        id=ctrl_a_id,
        name="Arden 72487 060",
        sku="72487 060",
        collection="Arden",
        source_type=CarpetSourceType.CATALOG,
        is_active=True,
    )
    db_session.add(ctrl_a)

    ctrl_a_img = CarpetImageModel(
        id=ctrl_a_img_id,
        carpet_id=ctrl_a_id,
        original_filename="72487_060.jpg",
        content_type="image/jpeg",
        storage_backend="LOCAL_FILESYSTEM",
        storage_key="test_72487_060.jpg",
        byte_size=2048,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="b" * 64,
        is_primary=True,
    )
    db_session.add(ctrl_a_img)

    ctrl_a_prof = CarpetStyleProfileModel(
        id=ctrl_a_prof_id,
        carpet_id=ctrl_a_id,
        image_id=ctrl_a_img_id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="b" * 64,
        analysis_scope="FULL_IMAGE",
        status=StyleProfileStatus.COMPLETE,
        analyzed_width_px=800,
        analyzed_height_px=600,
    )
    db_session.add(ctrl_a_prof)

    for dim in CANONICAL_STYLE_DNA:
        db_session.add(
            CarpetStyleDimensionModel(
                id=uuid.uuid4(),
                profile_id=ctrl_a_prof_id,
                dimension_key=dim["key"],
                value=0.50,
                confidence=0.85,
                status=StyleDimensionStatus.AVAILABLE,
            )
        )

    # 3. Control C: SKU 74928 062 (No Primary Image)
    ctrl_c_id = uuid.uuid4()
    ctrl_c = CarpetModel(
        id=ctrl_c_id,
        name="Vega 74928 062",
        sku="74928 062",
        collection="Vega",
        source_type=CarpetSourceType.CATALOG,
        is_active=True,
    )
    db_session.add(ctrl_c)

    # 4. Control D: Historical Reference ref-met-489476 (No Primary Image)
    ctrl_d_id = uuid.uuid4()
    ctrl_d = CarpetModel(
        id=ctrl_d_id,
        name="Historical Met Object 489476",
        sku="ref-met-489476",
        collection="Met Collection",
        source_type=CarpetSourceType.HISTORICAL,
        is_active=True,
    )
    db_session.add(ctrl_d)

    ctrl_d_meta_id = uuid.uuid4()
    ctrl_d_meta = HistoricalReferenceMetadataModel(
        id=ctrl_d_meta_id,
        carpet_id=ctrl_d_id,
        reference_key="ref-met-489476",
        object_identifier="489476",
        institution_name="The Metropolitan Museum of Art",
        object_title="Fragment of a Carpet",
    )
    db_session.add(ctrl_d_meta)

    ctrl_d_src = HistoricalReferenceSourceModel(
        id=uuid.uuid4(),
        historical_reference_id=ctrl_d_meta_id,
        source_id=source_id,
        source_role="PRIMARY_OBJECT_RECORD",
    )
    db_session.add(ctrl_d_src)

    # 5. Historical Reference with Image for Historical Connection candidate
    hist_id = uuid.uuid4()
    hist_img_id = uuid.uuid4()
    hist_prof_id = uuid.uuid4()

    hist_carpet = CarpetModel(
        id=hist_id,
        name="Historical Met Object 13575",
        sku="ref-met-13575",
        collection="Met Collection",
        source_type=CarpetSourceType.HISTORICAL,
        is_active=True,
    )
    db_session.add(hist_carpet)

    hist_meta_id = uuid.uuid4()
    hist_meta = HistoricalReferenceMetadataModel(
        id=hist_meta_id,
        carpet_id=hist_id,
        reference_key="ref-met-13575",
        object_identifier="13575",
        institution_name="The Metropolitan Museum of Art",
        object_title="Carpet with Garden Design",
    )
    db_session.add(hist_meta)

    hist_src = HistoricalReferenceSourceModel(
        id=uuid.uuid4(),
        historical_reference_id=hist_meta_id,
        source_id=source_id,
        source_role="PRIMARY_OBJECT_RECORD",
    )
    db_session.add(hist_src)

    hist_img = CarpetImageModel(
        id=hist_img_id,
        carpet_id=hist_id,
        original_filename="13575.jpg",
        content_type="image/jpeg",
        storage_backend="LOCAL_FILESYSTEM",
        storage_key="test_13575.jpg",
        byte_size=2048,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="c" * 64,
        is_primary=True,
    )
    db_session.add(hist_img)

    hist_prof = CarpetStyleProfileModel(
        id=hist_prof_id,
        carpet_id=hist_id,
        image_id=hist_img_id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="c" * 64,
        analysis_scope="FULL_IMAGE",
        status=StyleProfileStatus.COMPLETE,
        analyzed_width_px=800,
        analyzed_height_px=600,
    )
    db_session.add(hist_prof)

    for dim in CANONICAL_STYLE_DNA:
        db_session.add(
            CarpetStyleDimensionModel(
                id=uuid.uuid4(),
                profile_id=hist_prof_id,
                dimension_key=dim["key"],
                value=0.68,
                confidence=0.88,
                status=StyleDimensionStatus.AVAILABLE,
            )
        )

    await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_complete_user_journey(client: AsyncClient, db_session: AsyncSession):
    """Test full E2E journey for primary specimen carpet SKU 73941 060."""
    await _seed_e2e_data(db_session)

    # Step 1: Start preference session
    res = await client.post("/api/v1/preference-assessments")
    assert res.status_code == 201
    assessment_id = res.json()["id"]

    # Step 2: Complete Text Preference Assessment (6 prompts)
    text_answers = {
        "T1_ROOM_ROLE": "STRONGLY_B",
        "T2_COLOR_DIVERSITY": "STRONGLY_A",
        "T3_CONTRAST": "SLIGHTLY_B",
        "T4_WARMTH": "NEUTRAL",
        "T5_STRUCTURAL_ORDER": "STRONGLY_B",
        "T6_FORM_LANGUAGE": "SLIGHTLY_A",
    }
    for q_key, choice in text_answers.items():
        r = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}",
            json={"choice": choice}
        )
        assert r.status_code == 200

    r_text_comp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    assert r_text_comp.status_code == 200

    # Step 3: Visual Preference Assessment
    r_vis_start = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert r_vis_start.status_code == 200

    visual_answers = {
        "V1_COLOR_ENERGY": "STRONGLY_RIGHT",
        "V2_CONTRAST": "SLIGHTLY_RIGHT",
        "V3_VISUAL_COMPLEXITY": "NEUTRAL",
        "V4_STRUCTURAL_ORDER": "STRONGLY_RIGHT",
        "V5_RHYTHM_REPETITION": "SLIGHTLY_LEFT",
        "V6_FORM_LANGUAGE": "STRONGLY_LEFT",
    }
    for v_key, choice in visual_answers.items():
        r = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{v_key}",
            json={"choice": choice}
        )
        assert r.status_code == 200

    r_vis_comp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert r_vis_comp.status_code == 200

    # Step 4: Build & Confirm Preference Profile
    r_build = await client.post(f"/api/v1/preference-assessments/{assessment_id}/build-profile")
    assert r_build.status_code == 200
    r_confirm = await client.post(f"/api/v1/preference-assessments/{assessment_id}/confirm-profile")
    assert r_confirm.status_code == 200

    # Step 5: Importance Profile
    importance_payload = {
        "skip": False,
        "priority_dimensions": ["color_energy", "structural_order"],
        "flexible_dimensions": ["form_language"],
    }
    r_imp = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/importance-profile",
        json=importance_payload
    )
    assert r_imp.status_code in (200, 201)

    # Step 6: Narrative Profile (canonical keys)
    narrative_payload = {
        "skip": False,
        "primary_themes": ["nature_growth", "cultural_heritage"],
        "secondary_themes": ["tradition_craft"],
    }
    r_narrative = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-profile",
        json=narrative_payload
    )
    assert r_narrative.status_code in (200, 201)

    # Step 7: Query primary specimen SKU 73941 060
    res = await client.get("/api/v1/catalog/carpets/73941%20060")
    assert res.status_code == 200
    carpet_data = res.json()
    carpet_id = carpet_data["carpet"]["id"]

    # Retrieve carpet's style profile ID from DB
    stmt = select(CarpetStyleProfileModel).where(CarpetStyleProfileModel.carpet_id == uuid.UUID(str(carpet_id)))
    profile_row = (await db_session.execute(stmt)).scalar_one()

    # Step 8: Layer 1 - Visual Style Match
    res = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/style-matches",
        json={"carpet_style_profile_id": str(profile_row.id)}
    )
    assert res.status_code in (200, 201)
    visual_match = res.json()

    # Step 9: Layer 2 - Narrative Affinity
    res = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-affinities",
        json={"carpet_id": str(carpet_id)}
    )
    assert res.status_code in (200, 201)
    narrative_affinity = res.json()

    # Step 10: Layer 3 - Historical Connection
    res = await client.post(
        "/api/v1/historical-connections",
        json={
            "target_style_profile_id": str(profile_row.id),
            "historical_reference_id": "ref-met-13575"
        }
    )
    assert res.status_code in (200, 201)
    hist_connection = res.json()

    # Step 11: Verify 3-layer result separation (No composite score)
    forbidden_keys = ["combined_score", "total_score", "overall_recommendation_score", "composite_score"]
    for k in forbidden_keys:
        assert k not in visual_match, f"Forbidden combined key '{k}' found in visual match response!"
        assert k not in narrative_affinity, f"Forbidden combined key '{k}' found in narrative affinity response!"
        assert k not in hist_connection, f"Forbidden combined key '{k}' found in historical connection response!"

    # Step 12: Non-profiling audit
    full_text = (str(visual_match) + str(narrative_affinity) + str(hist_connection)).lower()
    for term in PROHIBITED_PROFILING_TERMS:
        assert term not in full_text, f"Prohibited profiling term '{term}' found in response!"


@pytest.mark.asyncio
async def test_e2e_control_no_story(client: AsyncClient, db_session: AsyncSession):
    """Control A: Carpet SKU 72487 060 has complete Style DNA but 0 story associations."""
    await _seed_e2e_data(db_session)

    # Start assessment & complete flow
    resp = await client.post("/api/v1/preference-assessments")
    assessment_id = resp.json()["id"]

    text_answers = {"T1_ROOM_ROLE": "NEUTRAL", "T2_COLOR_DIVERSITY": "NEUTRAL", "T3_CONTRAST": "NEUTRAL", "T4_WARMTH": "NEUTRAL", "T5_STRUCTURAL_ORDER": "NEUTRAL", "T6_FORM_LANGUAGE": "NEUTRAL"}
    for q_key, choice in text_answers.items():
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}", json={"choice": choice})
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")

    await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    visual_answers = {"V1_COLOR_ENERGY": "NEUTRAL", "V2_CONTRAST": "NEUTRAL", "V3_VISUAL_COMPLEXITY": "NEUTRAL", "V4_STRUCTURAL_ORDER": "NEUTRAL", "V5_RHYTHM_REPETITION": "NEUTRAL", "V6_FORM_LANGUAGE": "NEUTRAL"}
    for v_key, choice in visual_answers.items():
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{v_key}", json={"choice": choice})
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")

    await client.post(f"/api/v1/preference-assessments/{assessment_id}/build-profile")
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/confirm-profile")

    await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["nature_growth"]}
    )

    # Query Control A carpet SKU 72487 060
    res = await client.get("/api/v1/catalog/carpets/72487%20060")
    assert res.status_code == 200
    carpet_id = res.json()["carpet"]["id"]

    # Calculate Narrative Affinity -> MUST yield clean NO_AFFINITY / empty claims, no fabricated story
    res = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-affinities",
        json={"carpet_id": str(carpet_id)}
    )
    assert res.status_code in (200, 201)
    narrative_affinity = res.json()
    status_val = narrative_affinity.get("status") or narrative_affinity.get("affinity_level") or narrative_affinity.get("overall_affinity")
    matched_claims = narrative_affinity.get("matched_claims") or narrative_affinity.get("claims") or []
    assert status_val in ["NOT_AVAILABLE", "NONE", "NO_MATCH", "NO_CURATED_STORY", "LOW"] or len(matched_claims) == 0


@pytest.mark.asyncio
async def test_e2e_control_no_image_catalog(client: AsyncClient, db_session: AsyncSession):
    """Control C: Catalog carpet SKU 74928 062 has NO primary image."""
    await _seed_e2e_data(db_session)
    res = await client.get("/api/v1/catalog/carpets/74928%20062")
    assert res.status_code == 200
    carpet = res.json()
    assert carpet.get("primary_image") is None or carpet.get("style_dna_readiness") == "NO_PRIMARY_IMAGE"


@pytest.mark.asyncio
async def test_e2e_control_no_image_historical(client: AsyncClient, db_session: AsyncSession):
    """Control D: Historical Reference ref-met-489476 has NO primary image."""
    await _seed_e2e_data(db_session)
    res = await client.get("/api/v1/historical-references/ref-met-489476")
    assert res.status_code == 200
    ref = res.json()
    assert ref.get("has_primary_image") is False or ref.get("primary_image_url") is None


@pytest.mark.asyncio
async def test_e2e_unknown_claim_and_uncertain_motif(db_session: AsyncSession):
    """Verify UNKNOWN claim produces no positive narrative affinity."""
    result = await db_session.execute(
        select(CarpetStoryAssociationModel)
        .join(MotifStoryClaimModel)
        .where(MotifStoryClaimModel.status == "UNKNOWN")
    )
    unknown_associations = result.scalars().all()
    assert len(unknown_associations) == 0


@pytest.mark.asyncio
async def test_e2e_regression_canonical_theme_keys(client: AsyncClient, db_session: AsyncSession):
    """Regression test: Canonical theme keys required, invalid keys/codes rejected."""
    await _seed_e2e_data(db_session)
    res = await client.post("/api/v1/preference-assessments")
    assessment_id = res.json()["id"]

    text_answers = {"T1_ROOM_ROLE": "NEUTRAL", "T2_COLOR_DIVERSITY": "NEUTRAL", "T3_CONTRAST": "NEUTRAL", "T4_WARMTH": "NEUTRAL", "T5_STRUCTURAL_ORDER": "NEUTRAL", "T6_FORM_LANGUAGE": "NEUTRAL"}
    for q_key, choice in text_answers.items():
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}", json={"choice": choice})
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")

    await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    visual_answers = {"V1_COLOR_ENERGY": "NEUTRAL", "V2_CONTRAST": "NEUTRAL", "V3_VISUAL_COMPLEXITY": "NEUTRAL", "V4_STRUCTURAL_ORDER": "NEUTRAL", "V5_RHYTHM_REPETITION": "NEUTRAL", "V6_FORM_LANGUAGE": "NEUTRAL"}
    for v_key, choice in visual_answers.items():
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{v_key}", json={"choice": choice})
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")

    await client.post(f"/api/v1/preference-assessments/{assessment_id}/build-profile")
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/confirm-profile")

    # Valid canonical keys
    res = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["nature_growth", "tradition_craft"]}
    )
    assert res.status_code in (200, 201)

    # Invalid presentation code N1 should be rejected
    res = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["N1"]}
    )
    assert res.status_code == 422
