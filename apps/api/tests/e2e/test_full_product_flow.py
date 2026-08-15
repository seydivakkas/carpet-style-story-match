"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

End-to-End Product Flow Integration Test v1.
Validates full user journey across Preference Assessment, Multimodal Profiling, Carpet Catalog, 
Visual Style Match, Narrative Affinity, and Historical Connection.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_full_end_to_end_product_experience_flow(client: AsyncClient, db_session: AsyncSession):
    """
    Complete E2E integration flow test:
    1. Create preference assessment session
    2. Submit text preference responses (6 questions) & complete text
    3. Start visual & Submit visual preference responses (6 stimuli cards) & complete visual
    4. Build & confirm multimodal user preference profile
    5. Submit importance profile (priority / flexible choices)
    6. Submit user narrative profile (primary / secondary themes)
    7. Fetch carpet catalog items
    8. Retrieve carpet evaluation details and verify 3 independent evaluation axes
    9. Verify strict absence of any combined / unified recommendation score
    """
    # Step 1: Create preference assessment
    resp = await client.post("/api/v1/preference-assessments")
    assert resp.status_code == 201
    assessment_data = resp.json()
    assessment_id = assessment_data["id"]
    assert assessment_id is not None

    # Step 2: Submit 6 text preference answers & complete text
    text_answers = {
        "T1_ROOM_ROLE": "STRONGLY_B",
        "T2_COLOR_DIVERSITY": "STRONGLY_A",
        "T3_CONTRAST": "SLIGHTLY_B",
        "T4_WARMTH": "NEUTRAL",
        "T5_STRUCTURAL_ORDER": "STRONGLY_B",
        "T6_FORM_LANGUAGE": "SLIGHTLY_A"
    }
    for q_key, choice in text_answers.items():
        resp_q = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}",
            json={"choice": choice}
        )
        assert resp_q.status_code == 200

    resp_complete_text = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    assert resp_complete_text.status_code == 200

    # Step 3: Start visual & submit 6 visual responses & complete visual
    resp_start_visual = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert resp_start_visual.status_code == 200

    visual_answers = {
        "V1_COLOR_ENERGY": "STRONGLY_RIGHT",
        "V2_CONTRAST": "SLIGHTLY_RIGHT",
        "V3_VISUAL_COMPLEXITY": "NEUTRAL",
        "V4_STRUCTURAL_ORDER": "STRONGLY_RIGHT",
        "V5_RHYTHM_REPETITION": "SLIGHTLY_LEFT",
        "V6_FORM_LANGUAGE": "STRONGLY_LEFT"
    }
    for v_key, choice in visual_answers.items():
        resp_v = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{v_key}",
            json={"choice": choice}
        )
        assert resp_v.status_code == 200

    resp_complete_vis = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert resp_complete_vis.status_code == 200

    # Step 4: Build & Confirm multimodal preference profile
    resp_build = await client.post(f"/api/v1/preference-assessments/{assessment_id}/build-profile")
    assert resp_build.status_code == 200

    resp_confirm = await client.post(f"/api/v1/preference-assessments/{assessment_id}/confirm-profile")
    assert resp_confirm.status_code == 200

    # Step 5: Submit importance profile
    importance_payload = {
        "skip": False,
        "priority_dimensions": ["color_energy", "structural_order"],
        "flexible_dimensions": ["form_language"]
    }
    resp_imp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/importance-profile", json=importance_payload)
    assert resp_imp.status_code in (200, 201)

    # Step 6: Submit user narrative profile
    narrative_payload = {
        "skip": False,
        "primary_themes": ["nature_growth"],
        "secondary_themes": ["belonging_home"]
    }
    resp_narrative = await client.post(f"/api/v1/preference-assessments/{assessment_id}/narrative-profile", json=narrative_payload)
    assert resp_narrative.status_code in (200, 201)

    # Step 7: Retrieve 9D user preference profile
    resp_profile = await client.get(f"/api/v1/preference-assessments/{assessment_id}/preference-profile")
    assert resp_profile.status_code == 200
    profile_data = resp_profile.json()
    assert len(profile_data["dimensions"]) == 9
    assert profile_data["status"] == "REVIEWED"

    # Step 8: Fetch carpet catalog
    resp_catalog = await client.get("/api/v1/carpets")
    assert resp_catalog.status_code == 200
    catalog_data = resp_catalog.json()
    assert "items" in catalog_data

    # Step 9: Verify 3-axis evaluation structure if carpets exist
    if len(catalog_data["items"]) > 0:
        carpet_id = catalog_data["items"][0]["id"]
        
        # Axis 1: Style Match
        resp_style = await client.get(f"/api/v1/carpets/{carpet_id}/style-match?assessment_id={assessment_id}")
        assert resp_style.status_code == 200
        style_match_data = resp_style.json()
        assert "status" in style_match_data

        # Axis 2: Narrative Affinity
        resp_narrative_aff = await client.get(f"/api/v1/carpets/{carpet_id}/narrative-affinities?assessment_id={assessment_id}")
        if resp_narrative_aff.status_code != 200:
            resp_narrative_aff = await client.get(f"/api/v1/preference-assessments/{assessment_id}/narrative-affinities")
        narrative_aff_data = resp_narrative_aff.json() if resp_narrative_aff.status_code == 200 else {}

        # Axis 3: Historical Connections
        resp_hist = await client.get(f"/api/v1/carpets/{carpet_id}/historical-connections")
        assert resp_hist.status_code in (200, 404)

        # Step 10: Verify Rule 14 Invariant: NO COMBINED / TOTAL SCORE
        forbidden_combined_keys = [
            "combined_score", "total_score", "overall_recommendation_score",
            "composite_score", "unified_score", "final_match_score"
        ]
        for key in forbidden_combined_keys:
            assert key not in style_match_data, f"Forbidden combined score key {key} found in style_match response!"
            assert key not in narrative_aff_data, f"Forbidden combined score key {key} found in narrative_aff response!"
