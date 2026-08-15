import uuid
import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    VisualPreferenceProfileModel,
    PreferenceDimensionStatus,
    VisualChoiceEnum
)
from app.domain.preferences.constants import (
    VISUAL_PREFERENCE_STIMULI_VERSION,
    VISUAL_PREFERENCE_EVIDENCE_VERSION,
    VISUAL_CHOICE_DISPLAY_SCALE,
    VISUAL_EVIDENCE_MATRIX_WEIGHTS
)
from app.domain.preferences.visual_stimuli import (
    STIMULI_CATALOG,
    CANONICAL_VISUAL_CARDS,
    generate_and_save_all_stimuli,
    ProceduralStimulusGenerator
)
from app.domain.preferences.aggregator import VisualPreferenceAggregator
from app.domain.styledna import StyleDNAEngine

# Target static directory for tests
TEST_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "static", "stimuli", VISUAL_PREFERENCE_STIMULI_VERSION)

# ---------------------------------------------------------
# UNIT & CV ENGINE VALIDATION TESTS
# ---------------------------------------------------------

def test_visual_stimuli_catalog_and_canonical_mapping():
    assert len(CANONICAL_VISUAL_CARDS) == 6
    expected_cards = [
        "V1_COLOR_ENERGY",
        "V2_CONTRAST",
        "V3_VISUAL_COMPLEXITY",
        "V4_STRUCTURAL_ORDER",
        "V5_RHYTHM_REPETITION",
        "V6_FORM_LANGUAGE"
    ]
    assert CANONICAL_VISUAL_CARDS == expected_cards

def test_visual_evidence_matrix_shape():
    assert len(VISUAL_EVIDENCE_MATRIX_WEIGHTS) == 6
    for card, weights in VISUAL_EVIDENCE_MATRIX_WEIGHTS.items():
        assert len(weights) == 9
        # Each card must target exactly 1 dimension (weight = 1.0)
        assert sum(weights) == 1.0

def test_visual_aggregator_neutral_responses():
    directions = {card: 0.0 for card in CANONICAL_VISUAL_CARDS}
    dims = VisualPreferenceAggregator.aggregate(directions)
    dim_map = {d["dimension_key"]: d for d in dims}

    # Measured D1, D3, D5, D6, D7, D9
    for k in ["color_energy", "contrast", "visual_complexity", "structural_order", "rhythm_repetition", "form_language"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.MEASURED
        assert dim_map[k]["value"] == 0.50

    # Unmeasured D2, D4, D8
    for k in ["color_diversity", "warmth", "focal_strength"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.NOT_MEASURED
        assert dim_map[k]["value"] is None

def test_visual_aggregator_canonical_poles():
    # Canonical -1.0 (Low pole A)
    low_dirs = {card: -1.0 for card in CANONICAL_VISUAL_CARDS}
    dims_low = VisualPreferenceAggregator.aggregate(low_dirs)
    map_low = {d["dimension_key"]: d for d in dims_low}
    for k in ["color_energy", "contrast", "visual_complexity", "structural_order", "rhythm_repetition", "form_language"]:
        assert map_low[k]["value"] == 0.00

    # Canonical +1.0 (High pole B)
    high_dirs = {card: +1.0 for card in CANONICAL_VISUAL_CARDS}
    dims_high = VisualPreferenceAggregator.aggregate(high_dirs)
    map_high = {d["dimension_key"]: d for d in dims_high}
    for k in ["color_energy", "contrast", "visual_complexity", "structural_order", "rhythm_repetition", "form_language"]:
        assert map_high[k]["value"] == 1.00

def test_cv_engine_validation_on_generated_stimuli():
    hashes = generate_and_save_all_stimuli(TEST_STIMULI_DIR)
    assert len(hashes) == 12

    engine = StyleDNAEngine()
    results = {}

    print("\n--- VISUAL STIMULI CV ENGINE VALIDATION RESULTS ---")
    for key in CANONICAL_VISUAL_CARDS:
        target_dim = STIMULI_CATALOG[key]["target_dimension"]
        png_a_path = os.path.join(TEST_STIMULI_DIR, f"{key.lower()}_a.png")
        png_b_path = os.path.join(TEST_STIMULI_DIR, f"{key.lower()}_b.png")

        with open(png_a_path, "rb") as f:
            bytes_a = f.read()
        with open(png_b_path, "rb") as f:
            bytes_b = f.read()

        _, dims_a = engine.analyze(bytes_a)
        _, dims_b = engine.analyze(bytes_b)

        map_a = {d["key"]: d["value"] for d in dims_a}
        map_b = {d["key"]: d["value"] for d in dims_b}

        val_a = map_a[target_dim]
        val_b = map_b[target_dim]
        target_delta = round(val_b - val_a, 4)

        # Compute non-target deltas
        non_target_deltas = {
            dim: round(abs(map_b[dim] - map_a[dim]), 4)
            for dim in map_a.keys()
            if dim != target_dim and map_a[dim] is not None and map_b[dim] is not None
        }
        max_non_target_delta = max(non_target_deltas.values())

        results[key] = {
            "val_a": val_a,
            "val_b": val_b,
            "target_delta": target_delta,
            "non_target_deltas": non_target_deltas,
            "max_non_target_delta": max_non_target_delta,
            "map_a": map_a,
            "map_b": map_b
        }

        print(f"Card {key} (Target: {target_dim}): A={val_a}, B={val_b}, Delta={target_delta}, Max Non-Target={max_non_target_delta}")

        # Assert target delta >= 0.35
        assert target_delta >= 0.35, f"{key} target delta {target_delta} < 0.35 (A={val_a}, B={val_b})"

    # Check D6/D7 decoupling contamination
    v4_d7_contam = round(abs(results["V4_STRUCTURAL_ORDER"]["map_b"]["rhythm_repetition"] - results["V4_STRUCTURAL_ORDER"]["map_a"]["rhythm_repetition"]), 4)
    v5_d6_contam = round(abs(results["V5_RHYTHM_REPETITION"]["map_b"]["structural_order"] - results["V5_RHYTHM_REPETITION"]["map_a"]["structural_order"]), 4)
    v3_d7_contam = round(abs(results["V3_VISUAL_COMPLEXITY"]["map_b"]["rhythm_repetition"] - results["V3_VISUAL_COMPLEXITY"]["map_a"]["rhythm_repetition"]), 4)

    print(f"V3 D7 Contamination: {v3_d7_contam}")
    print(f"V4 D7 Contamination: {v4_d7_contam}")
    print(f"V5 D6 Contamination: {v5_d6_contam}")

    assert v4_d7_contam <= 0.15, f"V4 D7 contamination {v4_d7_contam} > 0.15"
    assert v5_d6_contam <= 0.15, f"V5 D6 contamination {v5_d6_contam} > 0.15"
    assert v3_d7_contam <= 0.15, f"V3 D7 contamination {v3_d7_contam} > 0.15"

# ---------------------------------------------------------
# API & INTEGRATION TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_get_meta_preference_visual_stimuli(client: AsyncClient):
    resp = await client.get("/api/v1/meta/preference-visual-stimuli")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_stimuli"] == 6
    assert len(data["stimuli"]) == 6
    assert data["stimuli"][0]["stimulus_key"] == "V1_COLOR_ENERGY"
    assert data["stimuli"][5]["stimulus_key"] == "V6_FORM_LANGUAGE"

@pytest.mark.asyncio
async def test_start_visual_requires_text_complete(client: AsyncClient):
    # Create assessment (status: TEXT_PENDING)
    create_resp = await client.post("/api/v1/preference-assessments")
    assessment_id = create_resp.json()["id"]

    # Try starting visual phase before text complete -> 409 Conflict
    start_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert start_resp.status_code == 409
    assert start_resp.json()["detail"]["code"] == "VISUAL_PHASE_REQUIRES_TEXT_COMPLETE"

@pytest.mark.asyncio
async def test_visual_preference_assessment_lifecycle(client: AsyncClient):
    # 1. Create Assessment & Complete Text Phase
    create_resp = await client.post("/api/v1/preference-assessments")
    assessment_id = create_resp.json()["id"]

    for q_key in ["T1_ROOM_ROLE", "T2_COLOR_DIVERSITY", "T3_CONTRAST", "T4_WARMTH", "T5_STRUCTURAL_ORDER", "T6_FORM_LANGUAGE"]:
        await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}",
            json={"choice": "NEUTRAL"}
        )
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")

    # 2. Start Visual Phase -> 200 OK (Generates 6 presentations)
    start_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert start_resp.status_code == 200
    presentations = start_resp.json()
    assert len(presentations) == 6

    # Verify presentation structure (semantic A/B identity is obfuscated)
    p1 = presentations[0]
    assert p1["stimulus_key"] == "V1_COLOR_ENERGY"
    assert "left_asset_url" in p1
    assert "right_asset_url" in p1
    assert "variant_a" not in p1  # Obfuscated from client

    # Idempotency check: calling start-visual again returns same presentations
    start_resp_2 = await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    assert start_resp_2.status_code == 200
    assert start_resp_2.json() == presentations

    # 3. Try completing visual before answering all 6 -> 409 Conflict
    incomplete_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert incomplete_resp.status_code == 409
    err = incomplete_resp.json()
    assert err["detail"]["code"] == "VISUAL_PREFERENCES_INCOMPLETE"
    assert err["detail"]["answered_count"] == 0

    # 4. Answer 5 visual cards
    cards = ["V1_COLOR_ENERGY", "V2_CONTRAST", "V3_VISUAL_COMPLEXITY", "V4_STRUCTURAL_ORDER", "V5_RHYTHM_REPETITION"]
    choices = ["STRONGLY_LEFT", "SLIGHTLY_LEFT", "NEUTRAL", "SLIGHTLY_RIGHT", "STRONGLY_RIGHT"]

    for card, choice in zip(cards, choices):
        put_resp = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{card}",
            json={"choice": choice}
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["stimulus_key"] == card
        assert put_resp.json()["choice"] == choice

    # 5. Answer 6th visual card (V6_FORM_LANGUAGE)
    await client.put(
        f"/api/v1/preference-assessments/{assessment_id}/visual-responses/V6_FORM_LANGUAGE",
        json={"choice": "NEUTRAL"}
    )

    # 6. Complete Visual Phase -> 200 OK
    complete_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert complete_resp.status_code == 200
    profile_data = complete_resp.json()
    assert profile_data["assessment_id"] == assessment_id
    assert len(profile_data["dimensions"]) == 9

    # Verify canonical dimension ordering D1 -> D9
    expected_dims = [
        "color_energy", "color_diversity", "contrast", "warmth",
        "visual_complexity", "structural_order", "rhythm_repetition",
        "focal_strength", "form_language"
    ]
    actual_dims = [d["key"] for d in profile_data["dimensions"]]
    assert actual_dims == expected_dims

    # Check unmeasured D2, D4, D8 in visual profile
    dim_map = {d["key"]: d for d in profile_data["dimensions"]}
    assert dim_map["color_diversity"]["status"] == "NOT_MEASURED"
    assert dim_map["color_diversity"]["value"] is None
    assert dim_map["warmth"]["status"] == "NOT_MEASURED"
    assert dim_map["warmth"]["value"] is None
    assert dim_map["focal_strength"]["status"] == "NOT_MEASURED"
    assert dim_map["focal_strength"]["value"] is None

    # Check assessment status updated to VISUAL_COMPLETE
    status_resp = await client.get(f"/api/v1/preference-assessments/{assessment_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "VISUAL_COMPLETE"

    # 7. Completed Visual Immutability Lock -> PUT fails with 409
    locked_resp = await client.put(
        f"/api/v1/preference-assessments/{assessment_id}/visual-responses/V1_COLOR_ENERGY",
        json={"choice": "STRONGLY_RIGHT"}
    )
    assert locked_resp.status_code == 409
    assert locked_resp.json()["detail"]["code"] == "VISUAL_PREFERENCES_ALREADY_COMPLETED"

    # 8. Idempotent complete re-POST -> 200 OK
    re_complete = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    assert re_complete.status_code == 200
    assert re_complete.json()["id"] == profile_data["id"]

    # 9. GET visual-profile -> 200 OK
    get_profile = await client.get(f"/api/v1/preference-assessments/{assessment_id}/visual-profile")
    assert get_profile.status_code == 200
    assert get_profile.json()["id"] == profile_data["id"]

@pytest.mark.asyncio
async def test_stimulus_asset_serving_endpoint(client: AsyncClient):
    # Valid asset URL -> 200 OK (image/svg+xml)
    asset_resp = await client.get(f"/api/v1/preference-stimuli/{VISUAL_PREFERENCE_STIMULI_VERSION}/v1_color_energy_a.svg")
    assert asset_resp.status_code == 200
    assert "image/svg+xml" in asset_resp.headers["content-type"]
    assert "<svg" in asset_resp.text

@pytest.mark.asyncio
async def test_visual_preference_cascade_delete(client: AsyncClient, db_session: AsyncSession):
    create_resp = await client.post("/api/v1/preference-assessments")
    assessment_id = create_resp.json()["id"]

    for q_key in ["T1_ROOM_ROLE", "T2_COLOR_DIVERSITY", "T3_CONTRAST", "T4_WARMTH", "T5_STRUCTURAL_ORDER", "T6_FORM_LANGUAGE"]:
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}", json={"choice": "NEUTRAL"})
    await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")

    await client.post(f"/api/v1/preference-assessments/{assessment_id}/start-visual")
    for s_key in CANONICAL_VISUAL_CARDS:
        await client.put(f"/api/v1/preference-assessments/{assessment_id}/visual-responses/{s_key}", json={"choice": "NEUTRAL"})
    
    comp_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-visual")
    profile_id = uuid.UUID(comp_resp.json()["id"])
    assessment_uuid = uuid.UUID(assessment_id)

    # Delete assessment directly from session
    assessment_obj = await db_session.get(PreferenceAssessmentModel, assessment_uuid)
    await db_session.delete(assessment_obj)
    await db_session.commit()

    # Verify visual profile deleted
    prof = await db_session.get(VisualPreferenceProfileModel, profile_id)
    assert prof is None
