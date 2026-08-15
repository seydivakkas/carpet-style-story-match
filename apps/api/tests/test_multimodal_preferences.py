import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.preferences.aggregator import (
    MultimodalPreferenceAggregator,
    PreferenceConfidenceCalculator
)
from app.db.models.preference_assessment import (
    PreferenceDimensionStatus,
    UserProfileStatusEnum,
    UserPreferenceProvenanceEnum,
    ConfidenceStatusEnum
)

@pytest.mark.anyio
async def test_multimodal_aggregator_unit():

    text_dims = {
        "color_energy": {"value": 0.25, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "color_diversity": {"value": 0.70, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "contrast": {"value": 0.25, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.2},
        "warmth": {"value": 0.80, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "visual_complexity": {"value": None, "status": PreferenceDimensionStatus.NOT_MEASURED, "evidence_weight": 0.0},
        "structural_order": {"value": 0.60, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "rhythm_repetition": {"value": None, "status": PreferenceDimensionStatus.NOT_MEASURED, "evidence_weight": 0.0},
        "focal_strength": {"value": 0.40, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 0.25},
        "form_language": {"value": 0.30, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
    }

    visual_dims = {
        "color_energy": {"value": 0.75, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "color_diversity": {"value": None, "status": PreferenceDimensionStatus.NOT_MEASURED, "evidence_weight": 0.0},
        "contrast": {"value": 0.75, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "warmth": {"value": None, "status": PreferenceDimensionStatus.NOT_MEASURED, "evidence_weight": 0.0},
        "visual_complexity": {"value": 0.65, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "structural_order": {"value": 0.60, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "rhythm_repetition": {"value": 0.85, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "focal_strength": {"value": None, "status": PreferenceDimensionStatus.NOT_MEASURED, "evidence_weight": 0.0},
        "form_language": {"value": 0.90, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
    }

    results = MultimodalPreferenceAggregator.aggregate(text_dims, visual_dims)
    res_map = {d["dimension_key"]: d for d in results}

    assert len(results) == 9
    for d in results:
        assert d["status"] == PreferenceDimensionStatus.MEASURED

    # D1 weighted merge: (0.25*1 + 0.75*1)/2 = 0.50
    assert res_map["color_energy"]["inferred_value"] == 0.50

    # D2 text only
    assert res_map["color_diversity"]["inferred_value"] == 0.70

    # D3 weighted merge: (0.25*1.2 + 0.75*1.0)/2.2 = 1.05 / 2.2 = 0.4773
    assert abs(res_map["contrast"]["inferred_value"] - 0.4773) < 0.001

    # D4 text only
    assert res_map["warmth"]["inferred_value"] == 0.80

    # D5 visual only
    assert res_map["visual_complexity"]["inferred_value"] == 0.65

    # D6 weighted merge: (0.60*1 + 0.60*1)/2 = 0.60
    assert res_map["structural_order"]["inferred_value"] == 0.60

    # D7 visual only
    assert res_map["rhythm_repetition"]["inferred_value"] == 0.85

    # D8 weak text only
    assert res_map["focal_strength"]["inferred_value"] == 0.40

    # D9 weighted merge: (0.30*1 + 0.90*1)/2 = 0.60
    assert res_map["form_language"]["inferred_value"] == 0.60


@pytest.mark.anyio
async def test_preference_confidence_calculator_unit():

    text_dims = {
        "color_energy": {"value": 0.80, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0}, # Full agreement
        "contrast": {"value": 0.00, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},     # Full conflict
        "structural_order": {"value": 0.25, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0}, # Partial agreement
        "color_diversity": {"value": 0.70, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0}, # Single source strong
        "focal_strength": {"value": 0.40, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 0.25},  # Single source weak
    }

    visual_dims = {
        "color_energy": {"value": 0.80, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "contrast": {"value": 1.00, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
        "structural_order": {"value": 0.75, "status": PreferenceDimensionStatus.MEASURED, "evidence_weight": 1.0},
    }

    results = PreferenceConfidenceCalculator.calculate(text_dims, visual_dims)
    res_map = {d["dimension_key"]: d for d in results}

    # D1: agreement = 1.0, coverage = 1.0 -> conf = 0.25*1 + 0.75*1 = 1.00
    assert res_map["color_energy"]["confidence"] == 1.00
    assert res_map["color_energy"]["agreement"] == 1.00

    # D3: conflict = 0.0 (diff 1.0) -> agreement = 0.0 -> conf = 0.25*1 + 0.75*0 = 0.25
    assert res_map["contrast"]["confidence"] == 0.25
    assert res_map["contrast"]["agreement"] == 0.00

    # D6: text 0.25, visual 0.75 -> diff 0.50 -> agreement 0.50 -> conf = 0.25*1 + 0.75*0.5 = 0.625
    assert res_map["structural_order"]["confidence"] == 0.625
    assert res_map["structural_order"]["agreement"] == 0.50

    # D2: single source strong (w=1.0) -> conf = 0.60 * 1.0 = 0.60
    assert res_map["color_diversity"]["confidence"] == 0.60

    # D8: single source weak (w=0.25) -> conf = 0.60 * 0.25 = 0.15
    assert res_map["focal_strength"]["confidence"] == 0.15

    # Range and validity checks
    for d in results:
        if d["status"] == ConfidenceStatusEnum.AVAILABLE:
            assert 0.0 <= d["confidence"] <= 1.0


@pytest.mark.anyio
async def test_build_multimodal_profile_requires_visual_complete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create assessment
        create_res = await client.post("/api/v1/preference-assessments")
        assert create_res.status_code == 201
        ass_id = create_res.json()["id"]

        # Try building profile when status is TEXT_PENDING -> 409 Conflict
        build_res = await client.post(f"/api/v1/preference-assessments/{ass_id}/build-profile")
        assert build_res.status_code == 409
        err = build_res.json()["detail"]
        assert err["code"] == "MULTIMODAL_PROFILE_REQUIRES_VISUAL_COMPLETE"


@pytest.mark.anyio
async def test_multimodal_profile_full_lifecycle_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create assessment
        create_res = await client.post("/api/v1/preference-assessments")
        assert create_res.status_code == 201
        ass_id = create_res.json()["id"]

        # 2. Answer text questions (6/6)
        text_answers = {
            "T1_ROOM_ROLE": "STRONGLY_B",
            "T2_COLOR_DIVERSITY": "STRONGLY_A",
            "T3_CONTRAST": "SLIGHTLY_B",
            "T4_WARMTH": "NEUTRAL",
            "T5_STRUCTURAL_ORDER": "STRONGLY_B",
            "T6_FORM_LANGUAGE": "SLIGHTLY_A"
        }
        for q_key, choice in text_answers.items():
            await client.put(f"/api/v1/preference-assessments/{ass_id}/text-responses/{q_key}", json={"choice": choice})
        await client.post(f"/api/v1/preference-assessments/{ass_id}/complete-text")
        await client.post(f"/api/v1/preference-assessments/{ass_id}/start-visual")

        # 3. Answer visual questions (6/6)
        visual_answers = {
            "V1_COLOR_ENERGY": "STRONGLY_RIGHT",
            "V2_CONTRAST": "SLIGHTLY_RIGHT",
            "V3_VISUAL_COMPLEXITY": "NEUTRAL",
            "V4_STRUCTURAL_ORDER": "STRONGLY_RIGHT",
            "V5_RHYTHM_REPETITION": "SLIGHTLY_LEFT",
            "V6_FORM_LANGUAGE": "STRONGLY_LEFT"
        }
        for v_key, choice in visual_answers.items():
            await client.put(f"/api/v1/preference-assessments/{ass_id}/visual-responses/{v_key}", json={"choice": choice})
        await client.post(f"/api/v1/preference-assessments/{ass_id}/complete-visual")

        # 4. Build multimodal profile
        build_res = await client.post(f"/api/v1/preference-assessments/{ass_id}/build-profile")
        assert build_res.status_code == 200
        pref_profile = build_res.json()
        assert pref_profile["profile_version"] == "multimodal-preference-v1"
        assert pref_profile["status"] == "DRAFT"
        assert len(pref_profile["dimensions"]) == 9

        # Canonical ordering D1..D9
        canonical_keys = ["color_energy", "color_diversity", "contrast", "warmth", "visual_complexity", "structural_order", "rhythm_repetition", "focal_strength", "form_language"]
        for idx, k in enumerate(canonical_keys):
            assert pref_profile["dimensions"][idx]["dimension_key"] == k
            assert pref_profile["dimensions"][idx]["status"] == "MEASURED"
            assert pref_profile["dimensions"][idx]["provenance"] == "INFERRED"

        # Check assessment status updated to PROFILE_READY
        ass_res = await client.get(f"/api/v1/preference-assessments/{ass_id}")
        assert ass_res.json()["status"] == "PROFILE_READY"

        # 5. Get Confidence Profile
        conf_res = await client.get(f"/api/v1/preference-assessments/{ass_id}/confidence-profile")
        assert conf_res.status_code == 200
        conf_profile = conf_res.json()
        assert conf_profile["confidence_version"] == "preference-confidence-v1"
        assert len(conf_profile["dimensions"]) == 9

        # D8 focal_strength weak evidence check
        d8_conf = next(d for d in conf_profile["dimensions"] if d["dimension_key"] == "focal_strength")
        assert d8_conf["confidence"] == 0.15
        assert d8_conf["modality_count"] == 1

        # 6. Override D1 (color_energy) to 0.85
        override_res = await client.put(
            f"/api/v1/preference-assessments/{ass_id}/preference-profile/dimensions/color_energy",
            json={"value": 0.85}
        )
        assert override_res.status_code == 200
        updated_pref = override_res.json()
        d1_dim = next(d for d in updated_pref["dimensions"] if d["dimension_key"] == "color_energy")
        assert d1_dim["final_value"] == 0.85
        assert d1_dim["provenance"] == "USER_OVERRIDDEN"
        assert d1_dim["inferred_value"] is not None # Preserved!

        # Verify confidence is UNCHANGED after override
        conf_res_after = await client.get(f"/api/v1/preference-assessments/{ass_id}/confidence-profile")
        d1_conf_after = next(d for d in conf_res_after.json()["dimensions"] if d["dimension_key"] == "color_energy")
        assert d1_conf_after["confidence"] is not None

        # 7. Confirm profile review
        confirm_res = await client.post(f"/api/v1/preference-assessments/{ass_id}/confirm-profile")
        assert confirm_res.status_code == 200
        reviewed_profile = confirm_res.json()
        assert reviewed_profile["status"] == "REVIEWED"

        # Check provenance: non-overridden dims become USER_CONFIRMED, overridden stays USER_OVERRIDDEN
        d1_rev = next(d for d in reviewed_profile["dimensions"] if d["dimension_key"] == "color_energy")
        d2_rev = next(d for d in reviewed_profile["dimensions"] if d["dimension_key"] == "color_diversity")
        assert d1_rev["provenance"] == "USER_OVERRIDDEN"
        assert d2_rev["provenance"] == "USER_CONFIRMED"

        # Check assessment status updated to PROFILE_REVIEWED
        ass_res_rev = await client.get(f"/api/v1/preference-assessments/{ass_id}")
        assert ass_res_rev.json()["status"] == "PROFILE_REVIEWED"

        # 8. Attempt override after review -> 409 Conflict
        override_lock_res = await client.put(
            f"/api/v1/preference-assessments/{ass_id}/preference-profile/dimensions/color_diversity",
            json={"value": 0.90}
        )
        assert override_lock_res.status_code == 409
        assert override_lock_res.json()["detail"]["code"] == "PREFERENCE_PROFILE_ALREADY_REVIEWED"


@pytest.mark.anyio
async def test_build_profile_and_confirm_idempotency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create and complete assessment
        create_res = await client.post("/api/v1/preference-assessments")
        ass_id = create_res.json()["id"]

        for q_key in ["T1_ROOM_ROLE", "T2_COLOR_DIVERSITY", "T3_CONTRAST", "T4_WARMTH", "T5_STRUCTURAL_ORDER", "T6_FORM_LANGUAGE"]:
            await client.put(f"/api/v1/preference-assessments/{ass_id}/text-responses/{q_key}", json={"choice": "NEUTRAL"})
        await client.post(f"/api/v1/preference-assessments/{ass_id}/complete-text")
        await client.post(f"/api/v1/preference-assessments/{ass_id}/start-visual")

        for v_key in ["V1_COLOR_ENERGY", "V2_CONTRAST", "V3_VISUAL_COMPLEXITY", "V4_STRUCTURAL_ORDER", "V5_RHYTHM_REPETITION", "V6_FORM_LANGUAGE"]:
            await client.put(f"/api/v1/preference-assessments/{ass_id}/visual-responses/{v_key}", json={"choice": "NEUTRAL"})
        await client.post(f"/api/v1/preference-assessments/{ass_id}/complete-visual")

        # Build 1
        build1 = await client.post(f"/api/v1/preference-assessments/{ass_id}/build-profile")
        assert build1.status_code == 200
        prof_id_1 = build1.json()["id"]

        # Build 2 (Idempotent call)
        build2 = await client.post(f"/api/v1/preference-assessments/{ass_id}/build-profile")
        assert build2.status_code == 200
        prof_id_2 = build2.json()["id"]
        assert prof_id_1 == prof_id_2

        # Confirm 1
        conf1 = await client.post(f"/api/v1/preference-assessments/{ass_id}/confirm-profile")
        assert conf1.status_code == 200
        assert conf1.json()["status"] == "REVIEWED"

        # Confirm 2 (Idempotent call)
        conf2 = await client.post(f"/api/v1/preference-assessments/{ass_id}/confirm-profile")
        assert conf2.status_code == 200
        assert conf2.json()["status"] == "REVIEWED"
