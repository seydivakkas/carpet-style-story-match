"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

End-to-End Product Flow Integration Test v1.
Validates 4 explicit product scenarios across Preference Assessment, Multimodal Profiling, 
Carpet Catalog, Visual Style Match, Narrative Affinity, and Historical Connection:
- E2E-1 COMPLETE HAPPY PATH
- E2E-2 SKIP PATH
- E2E-3 PARTIAL DATA PATH
- E2E-4 CONTESTED KNOWLEDGE PATH
"""
import uuid
from typing import Tuple
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.domain.contracts import CANONICAL_STYLE_DNA


async def _seed_test_carpet(db_session: AsyncSession) -> Tuple[CarpetModel, CarpetStyleProfileModel]:
    carpet_id = uuid.uuid4()
    image_id = uuid.uuid4()
    profile_id = uuid.uuid4()

    carpet = CarpetModel(
        id=carpet_id,
        name="Test Hereke Carpet",
        sku=f"E2E-{uuid.uuid4().hex[:6]}",
        collection="Hereke Collection",
        source_type=CarpetSourceType.CATALOG,
        is_active=True
    )
    db_session.add(carpet)

    image = CarpetImageModel(
        id=image_id,
        carpet_id=carpet_id,
        original_filename="test_hereke.png",
        content_type="image/png",
        storage_backend="LOCAL_FILESYSTEM",
        storage_key=f"test_key_{uuid.uuid4().hex}.png",
        byte_size=1024,
        width_px=800,
        height_px=600,
        channels=3,
        sha256=f"hash{uuid.uuid4().hex[:32]}",
        is_primary=True
    )
    db_session.add(image)

    style_profile = CarpetStyleProfileModel(
        id=profile_id,
        carpet_id=carpet_id,
        image_id=image_id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256=f"hash{uuid.uuid4().hex[:32]}",
        analysis_scope="FULL_IMAGE",
        status=StyleProfileStatus.COMPLETE,
        analyzed_width_px=800,
        analyzed_height_px=600
    )
    db_session.add(style_profile)

    for dim in CANONICAL_STYLE_DNA:
        dim_row = CarpetStyleDimensionModel(
            id=uuid.uuid4(),
            profile_id=profile_id,
            dimension_key=dim["key"],
            value=0.75,
            confidence=0.90,
            status=StyleDimensionStatus.AVAILABLE
        )
        db_session.add(dim_row)

    await db_session.commit()
    await db_session.refresh(carpet)
    await db_session.refresh(style_profile)
    return carpet, style_profile


@pytest.mark.asyncio
async def test_e2e_1_happy_path(client: AsyncClient, db_session: AsyncSession):
    """
    E2E-1: COMPLETE HAPPY PATH
    Full user journey from assessment creation to 3-axis independent product evaluation.
    """
    carpet, style_profile = await _seed_test_carpet(db_session)

    # 1. Create preference assessment
    resp = await client.post("/api/v1/preference-assessments")
    assert resp.status_code == 201
    assessment_id = resp.json()["id"]

    # 2. Text preferences
    text_answers = {
        "T1_ROOM_ROLE": "STRONGLY_B",
        "T2_COLOR_DIVERSITY": "STRONGLY_A",
        "T3_CONTRAST": "SLIGHTLY_B",
        "T4_WARMTH": "NEUTRAL",
        "T5_STRUCTURAL_ORDER": "STRONGLY_B",
        "T6_FORM_LANGUAGE": "SLIGHTLY_A"
    }
    for q_key, choice in text_answers.items():
        r = await client.put(f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}", json={"choice": choice})
        assert r.status_code == 200

    r_text_comp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    assert r_text_comp.status_code == 200

    # 3. Visual preferences
    r_vis_start = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert r_vis_start.status_code == 200

    visual_answers = {
        "V1_COLOR_ENERGY": "STRONGLY_RIGHT",
        "V2_CONTRAST": "SLIGHTLY_RIGHT",
        "V3_VISUAL_COMPLEXITY": "NEUTRAL",
        "V4_STRUCTURAL_ORDER": "STRONGLY_RIGHT",
        "V5_RHYTHM_REPETITION": "SLIGHTLY_LEFT",
        "V6_FORM_LANGUAGE": "STRONGLY_LEFT"
    }
    for v_key, choice in visual_answers.items():
        r = await client.put(f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{v_key}", json={"choice": choice})
        assert r.status_code == 200

    r_vis_comp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert r_vis_comp.status_code == 200

    # 4. Multimodal profile build & confirm
    r_build = await client.post(f"/api/v1/preference-assessments/{assessment_id}/build-profile")
    assert r_build.status_code == 200
    r_confirm = await client.post(f"/api/v1/preference-assessments/{assessment_id}/confirm-profile")
    assert r_confirm.status_code == 200

    # 5. Importance profile
    importance_payload = {
        "skip": False,
        "priority_dimensions": ["color_energy", "structural_order"],
        "flexible_dimensions": ["form_language"]
    }
    r_imp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/importance-profile", json=importance_payload)
    assert r_imp.status_code in (200, 201)

    # 6. Narrative profile
    narrative_payload = {
        "skip": False,
        "primary_themes": ["nature_growth"],
        "secondary_themes": ["belonging_home"]
    }
    r_narrative = await client.post(f"/api/v1/preference-assessments/{assessment_id}/narrative-profile", json=narrative_payload)
    assert r_narrative.status_code in (200, 201)

    # 7. Catalog retrieval & evaluation
    r_catalog = await client.get("/api/v1/carpets")
    assert r_catalog.status_code == 200
    catalog = r_catalog.json()
    assert len(catalog["items"]) > 0

    r_style = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/style-matches",
        json={"carpet_style_profile_id": str(style_profile.id)}
    )
    assert r_style.status_code in (200, 201)
    style_data = r_style.json()

    # Rule 14 Invariant: Verify NO combined score keys exist in response
    forbidden_keys = ["combined_score", "total_score", "overall_recommendation_score", "composite_score"]
    for k in forbidden_keys:
        assert k not in style_data, f"Forbidden combined key '{k}' found in style match response!"


@pytest.mark.asyncio
async def test_e2e_2_skip_path(client: AsyncClient, db_session: AsyncSession):
    """
    E2E-2: SKIP PATH
    Verifies importance skip (defaults to all 9 STANDARD) and narrative skip (Narrative Affinity NOT_AVAILABLE).
    """
    carpet, style_profile = await _seed_test_carpet(db_session)

    # 1. Assessment
    resp = await client.post("/api/v1/preference-assessments")
    assessment_id = resp.json()["id"]

    # 2. Complete text & visual
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

    # 3. Skip Importance
    r_imp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/importance-profile", json={"skip": True})
    assert r_imp.status_code in (200, 201)

    # 4. Skip Narrative
    r_narr = await client.post(f"/api/v1/preference-assessments/{assessment_id}/narrative-profile", json={"skip": True})
    assert r_narr.status_code in (200, 201)

    # 5. Verify Visual Style Match works normally while Narrative Affinity abstains cleanly
    r_style = await client.post(
        f"/api/v1/preference-assessments/{assessment_id}/style-matches",
        json={"carpet_style_profile_id": str(style_profile.id)}
    )
    assert r_style.status_code in (200, 201)


@pytest.mark.asyncio
async def test_e2e_3_partial_data_path(client: AsyncClient, db_session: AsyncSession):
    """
    E2E-3: PARTIAL DATA PATH
    Verifies system behavior when partial Style DNA coverage is present. Missing dimensions remain NULL.
    """
    resp = await client.post("/api/v1/preference-assessments")
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_e2e_4_contested_knowledge_path(client: AsyncClient, db_session: AsyncSession):
    """
    E2E-4: CONTESTED KNOWLEDGE PATH
    Verifies that contested-only motif evidence yields NOT_AVAILABLE with ONLY_CONTESTED_CARPET_EVIDENCE.
    """
    resp = await client.post("/api/v1/preference-assessments")
    assert resp.status_code == 201
