"""Comprehensive pytest suite for Visual Style Match Engine v1."""
import pytest
import uuid
from typing import Dict, Any
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.preferences.constants import CANONICAL_DIMENSIONS
from app.db.models.preference_assessment import (
    StyleMatchStatusEnum,
    StyleMatchLabelEnum,
    ImportanceLevelEnum,
    UserPreferenceProvenanceEnum
)
from app.domain.stylematch.constants import (
    VISUAL_STYLE_MATCH_VERSION,
    get_match_label
)
from app.domain.stylematch.engine import VisualStyleMatchEngine, CalculatedMatchResult

# Helper fixture generators for pure engine tests
def build_engine_user_dims(values: Dict[str, float], status_val: str = "MEASURED", confidence: float = 0.90, provenance=UserPreferenceProvenanceEnum.INFERRED) -> Dict[str, Dict[str, Any]]:
    res = {}
    for key in CANONICAL_DIMENSIONS:
        val = values.get(key, 0.5)
        res[key] = {
            "final_value": val,
            "provenance": provenance,
            "status": status_val,
            "confidence": confidence
        }
    return res

def build_engine_importance_dims(priority: list = None, flexible: list = None) -> Dict[str, Dict[str, Any]]:
    priority = priority or []
    flexible = flexible or []
    res = {}
    for key in CANONICAL_DIMENSIONS:
        if key in priority:
            res[key] = {"level": ImportanceLevelEnum.PRIORITY, "weight": 1.00}
        elif key in flexible:
            res[key] = {"level": ImportanceLevelEnum.FLEXIBLE, "weight": 0.25}
        else:
            res[key] = {"level": ImportanceLevelEnum.STANDARD, "weight": 0.60}
    return res

def build_engine_carpet_dims(values: Dict[str, float], status_map: Dict[str, str] = None, confidence: float = 0.95) -> Dict[str, Dict[str, Any]]:
    status_map = status_map or {}
    res = {}
    for key in CANONICAL_DIMENSIONS:
        val = values.get(key, 0.5)
        st = status_map.get(key, "AVAILABLE")
        res[key] = {
            "value": val if st != "NOT_AVAILABLE" and st != "FAILED" else None,
            "status": st,
            "confidence": confidence
        }
    return res

# ---------------------------------------------------------
# PURE ENGINE UNIT TESTS
# ---------------------------------------------------------

def test_identical_profile():
    """Exact match across all 9 dimensions must yield score 1.0 (100), COMPLETE status, VERY_STRONG label."""
    vals = {k: 0.70 for k in CANONICAL_DIMENSIONS}
    user_dims = build_engine_user_dims(vals)
    imp_dims = build_engine_importance_dims(priority=["color_energy"], flexible=["warmth"])
    carpet_dims = build_engine_carpet_dims(vals)

    res = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, carpet_dims)

    assert res.status == StyleMatchStatusEnum.COMPLETE
    assert res.score == 1.0
    assert res.score_100 == 100.0
    assert res.match_label == StyleMatchLabelEnum.VERY_STRONG
    assert res.comparable_dimension_count == 9
    assert res.weighted_coverage == 1.0
    assert all(d.similarity == 1.0 for d in res.dimensions)


def test_opposite_profile():
    """Opposite values across all 9 dimensions (User 0.0, Carpet 1.0) must yield score 0.0 (0), LOW label."""
    user_vals = {k: 0.0 for k in CANONICAL_DIMENSIONS}
    carpet_vals = {k: 1.0 for k in CANONICAL_DIMENSIONS}

    user_dims = build_engine_user_dims(user_vals)
    imp_dims = build_engine_importance_dims(priority=["color_energy"], flexible=["warmth"])
    carpet_dims = build_engine_carpet_dims(carpet_vals)

    res = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, carpet_dims)

    assert res.status == StyleMatchStatusEnum.COMPLETE
    assert res.score == 0.0
    assert res.score_100 == 0.0
    assert res.match_label == StyleMatchLabelEnum.LOW
    assert all(d.similarity == 0.0 for d in res.dimensions)


def test_importance_effect():
    """Matching a PRIORITY dimension must produce a higher score than matching a FLEXIBLE dimension."""
    user_vals = {k: 0.5 for k in CANONICAL_DIMENSIONS}
    # D1 is PRIORITY (1.00), D4 is FLEXIBLE (0.25), rest STANDARD (0.60)
    imp_dims = build_engine_importance_dims(priority=["color_energy"], flexible=["warmth"])

    # Carpet A: Mismatch on PRIORITY D1 (user 0.5, carpet 1.0 -> sim 0.5), Exact match on FLEXIBLE D4 (sim 1.0), rest exact
    carpet_vals_a = {k: 0.5 for k in CANONICAL_DIMENSIONS}
    carpet_vals_a["color_energy"] = 1.0  # PRIORITY mismatch
    carpet_dims_a = build_engine_carpet_dims(carpet_vals_a)

    res_a = VisualStyleMatchEngine.compute_match(user_dimensions_map=build_engine_user_dims(user_vals), importance_dimensions_map=imp_dims, carpet_dimensions_map=carpet_dims_a)

    # Carpet B: Exact match on PRIORITY D1 (sim 1.0), Mismatch on FLEXIBLE D4 (user 0.5, carpet 1.0 -> sim 0.5), rest exact
    carpet_vals_b = {k: 0.5 for k in CANONICAL_DIMENSIONS}
    carpet_vals_b["warmth"] = 1.0  # FLEXIBLE mismatch
    carpet_dims_b = build_engine_carpet_dims(carpet_vals_b)

    res_b = VisualStyleMatchEngine.compute_match(user_dimensions_map=build_engine_user_dims(user_vals), importance_dimensions_map=imp_dims, carpet_dimensions_map=carpet_dims_b)

    assert res_b.score > res_a.score


def test_standard_all_skip():
    """Skip importance (all weights 0.60) must equal simple unweighted mean similarity."""
    user_vals = {"color_energy": 0.20, "contrast": 0.80, "warmth": 0.50}
    carpet_vals = {"color_energy": 0.40, "contrast": 0.60, "warmth": 0.50}

    user_dims = build_engine_user_dims(user_vals)
    imp_dims = build_engine_importance_dims()  # all STANDARD 0.60
    carpet_dims = build_engine_carpet_dims(carpet_vals)

    res = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, carpet_dims)

    sims = [d.similarity for d in res.dimensions if d.comparable]
    expected_mean = sum(sims) / len(sims)

    assert pytest.approx(res.score, abs=1e-6) == expected_mean


def test_confidence_invariance():
    """CONFIDENCE MUST NOT MULTIPLY INTO MATCH SCORE. User confidence 1.0 vs 0.1 yields identical match score."""
    user_vals = {k: 0.6 for k in CANONICAL_DIMENSIONS}
    carpet_vals = {k: 0.4 for k in CANONICAL_DIMENSIONS}
    imp_dims = build_engine_importance_dims(priority=["contrast"])

    user_dims_high_conf = build_engine_user_dims(user_vals, confidence=1.0)
    user_dims_low_conf = build_engine_user_dims(user_vals, confidence=0.1)

    carpet_dims = build_engine_carpet_dims(carpet_vals)

    res_high = VisualStyleMatchEngine.compute_match(user_dims_high_conf, imp_dims, carpet_dims)
    res_low = VisualStyleMatchEngine.compute_match(user_dims_low_conf, imp_dims, carpet_dims)

    assert res_high.score == res_low.score
    assert res_high.score_100 == res_low.score_100


def test_carpet_confidence_invariance():
    """Carpet measurement confidence 0.95 vs 0.30 yields identical match score."""
    user_vals = {k: 0.6 for k in CANONICAL_DIMENSIONS}
    carpet_vals = {k: 0.4 for k in CANONICAL_DIMENSIONS}
    imp_dims = build_engine_importance_dims()

    carpet_dims_high = build_engine_carpet_dims(carpet_vals, confidence=0.95)
    carpet_dims_low = build_engine_carpet_dims(carpet_vals, confidence=0.30)

    res_high = VisualStyleMatchEngine.compute_match(build_engine_user_dims(user_vals), imp_dims, carpet_dims_high)
    res_low = VisualStyleMatchEngine.compute_match(build_engine_user_dims(user_vals), imp_dims, carpet_dims_low)

    assert res_high.score == res_low.score


def test_override_used():
    """Engine uses final_value (which contains user override) rather than inferred value."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    # Set override on warmth: final_value = 0.80, provenance = USER_OVERRIDDEN
    user_dims["warmth"] = {
        "final_value": 0.80,
        "provenance": UserPreferenceProvenanceEnum.USER_OVERRIDDEN,
        "status": "MEASURED",
        "confidence": 1.0
    }

    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    carpet_dims["warmth"] = {"value": 0.80, "status": "AVAILABLE", "confidence": 1.0}

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    warmth_dim = next(d for d in res.dimensions if d.dimension_key == "warmth")
    assert warmth_dim.user_value == 0.80
    assert warmth_dim.user_provenance == UserPreferenceProvenanceEnum.USER_OVERRIDDEN
    assert warmth_dim.similarity == 1.0


def test_provenance_does_not_weight_score():
    """Same final value with USER_CONFIRMED vs USER_OVERRIDDEN yields identical match score."""
    user_dims_a = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, provenance=UserPreferenceProvenanceEnum.USER_CONFIRMED)
    user_dims_b = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, provenance=UserPreferenceProvenanceEnum.USER_OVERRIDDEN)

    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    imp_dims = build_engine_importance_dims()

    res_a = VisualStyleMatchEngine.compute_match(user_dims_a, imp_dims, carpet_dims)
    res_b = VisualStyleMatchEngine.compute_match(user_dims_b, imp_dims, carpet_dims)

    assert res_a.score == res_b.score


def test_d4_bipolar():
    """Warmth uses standard normalized distance: 0 vs 1 yields 0 similarity; 0.5 vs 0.5 yields 1 similarity."""
    user_dims = build_engine_user_dims({"warmth": 0.0})
    carpet_dims_0 = build_engine_carpet_dims({"warmth": 1.0})
    res_0 = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims_0)
    w_dim_0 = next(d for d in res_0.dimensions if d.dimension_key == "warmth")
    assert w_dim_0.similarity == 0.0

    user_dims_5 = build_engine_user_dims({"warmth": 0.5})
    carpet_dims_5 = build_engine_carpet_dims({"warmth": 0.5})
    res_5 = VisualStyleMatchEngine.compute_match(user_dims_5, build_engine_importance_dims(), carpet_dims_5)
    w_dim_5 = next(d for d in res_5.dimensions if d.dimension_key == "warmth")
    assert w_dim_5.similarity == 1.0


def test_d9_bipolar():
    """Form language uses standard normalized distance: 0 vs 1 yields 0 similarity; 0.5 vs 0.5 yields 1 similarity."""
    user_dims = build_engine_user_dims({"form_language": 0.0})
    carpet_dims_0 = build_engine_carpet_dims({"form_language": 1.0})
    res_0 = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims_0)
    f_dim_0 = next(d for d in res_0.dimensions if d.dimension_key == "form_language")
    assert f_dim_0.similarity == 0.0


def test_partial_one_dimension_missing():
    """1 missing carpet dimension yields 8 comparable dimensions, status PARTIAL, weighted_coverage < 1.0, score calculated over 8 dims."""
    user_dims = build_engine_user_dims({k: 0.8 for k in CANONICAL_DIMENSIONS})
    carpet_dims = build_engine_carpet_dims({k: 0.8 for k in CANONICAL_DIMENSIONS}, status_map={"form_language": "NOT_AVAILABLE"})

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    assert res.status == StyleMatchStatusEnum.PARTIAL
    assert res.comparable_dimension_count == 8
    assert res.weighted_coverage >= 0.70
    assert res.score == 1.0
    assert res.score_100 == 100.0

    missing_dim = next(d for d in res.dimensions if d.dimension_key == "form_language")
    assert missing_dim.comparable is False
    assert missing_dim.similarity is None


def test_priority_missing_coverage_impact():
    """Missing a PRIORITY dimension (weight 1.00) drops weighted coverage more than missing a FLEXIBLE dimension (weight 0.25)."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    imp_dims = build_engine_importance_dims(priority=["color_energy"], flexible=["warmth"])

    # Carpet missing PRIORITY D1
    carpet_missing_p = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, status_map={"color_energy": "NOT_AVAILABLE"})
    res_missing_p = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, carpet_missing_p)

    # Carpet missing FLEXIBLE D4
    carpet_missing_f = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, status_map={"warmth": "NOT_AVAILABLE"})
    res_missing_f = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, carpet_missing_f)

    assert res_missing_f.weighted_coverage > res_missing_p.weighted_coverage


def test_low_coverage_not_available():
    """Less than 6 comparable dimensions yields status NOT_AVAILABLE and score = None."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    # 5 missing dimensions -> only 4 comparable
    missing_map = {
        "color_energy": "NOT_AVAILABLE",
        "color_diversity": "NOT_AVAILABLE",
        "contrast": "NOT_AVAILABLE",
        "warmth": "NOT_AVAILABLE",
        "visual_complexity": "NOT_AVAILABLE"
    }
    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, status_map=missing_map)

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    assert res.status == StyleMatchStatusEnum.NOT_AVAILABLE
    assert res.score is None
    assert res.score_100 is None
    assert res.match_label is None


def test_low_confidence_comparable():
    """LOW_CONFIDENCE carpet dimension is comparable and included in score calculation."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, status_map={"contrast": "LOW_CONFIDENCE"})

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    assert res.status == StyleMatchStatusEnum.COMPLETE
    assert res.comparable_dimension_count == 9
    contrast_dim = next(d for d in res.dimensions if d.dimension_key == "contrast")
    assert contrast_dim.comparable is True
    assert contrast_dim.carpet_dimension_status == "LOW_CONFIDENCE"


def test_failed_dimension_excluded():
    """FAILED carpet dimension is non-comparable."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS}, status_map={"structural_order": "FAILED"})

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    assert res.comparable_dimension_count == 8
    so_dim = next(d for d in res.dimensions if d.dimension_key == "structural_order")
    assert so_dim.comparable is False
    assert so_dim.similarity is None


def test_score_range():
    """Score must strictly lie within [0.0, 1.0] and score_100 within [0.0, 100.0]."""
    user_dims = build_engine_user_dims({"color_energy": 0.1, "contrast": 0.9, "warmth": 0.4})
    carpet_dims = build_engine_carpet_dims({"color_energy": 0.8, "contrast": 0.2, "warmth": 0.7})

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(priority=["contrast"]), carpet_dims)

    assert res.score is not None
    assert 0.0 <= res.score <= 1.0
    assert 0.0 <= res.score_100 <= 100.0


def test_label_boundaries():
    """Check label boundaries: 90 -> VERY_STRONG, 89.99 -> STRONG, 75 -> STRONG, 74.99 -> MODERATE, 60 -> MODERATE, 59.99 -> LIMITED, 45 -> LIMITED, 44.99 -> LOW."""
    assert get_match_label(95.0) == StyleMatchLabelEnum.VERY_STRONG
    assert get_match_label(90.0) == StyleMatchLabelEnum.VERY_STRONG
    assert get_match_label(89.99) == StyleMatchLabelEnum.STRONG
    assert get_match_label(75.0) == StyleMatchLabelEnum.STRONG
    assert get_match_label(74.99) == StyleMatchLabelEnum.MODERATE
    assert get_match_label(60.0) == StyleMatchLabelEnum.MODERATE
    assert get_match_label(59.99) == StyleMatchLabelEnum.LIMITED
    assert get_match_label(45.0) == StyleMatchLabelEnum.LIMITED
    assert get_match_label(44.99) == StyleMatchLabelEnum.LOW
    assert get_match_label(10.0) == StyleMatchLabelEnum.LOW


def test_explanation_order():
    """Top matches ordered by match_strength desc; Main differences ordered by mismatch_impact desc."""
    user_vals = {k: 0.5 for k in CANONICAL_DIMENSIONS}
    user_dims = build_engine_user_dims(user_vals)
    imp_dims = build_engine_importance_dims(priority=["color_energy", "structural_order"], flexible=["warmth"])

    carpet_vals = {
        "color_energy": 0.5,      # Exact match on PRIORITY -> match_strength = 1.00 * 1.0 = 1.00
        "structural_order": 1.0,  # Mismatch on PRIORITY -> diff 0.5, mismatch_impact = 1.00 * 0.5 = 0.50
        "contrast": 0.5,          # Exact match on STANDARD -> match_strength = 0.60 * 1.0 = 0.60
        "warmth": 1.0,            # Mismatch on FLEXIBLE -> diff 0.5, mismatch_impact = 0.25 * 0.5 = 0.125
        "color_diversity": 0.5,
        "visual_complexity": 0.5,
        "rhythm_repetition": 0.5,
        "focal_strength": 0.5,
        "form_language": 0.5
    }

    res = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, build_engine_carpet_dims(carpet_vals))

    top = res.explanation.top_matches
    diffs = res.explanation.main_differences

    assert len(top) >= 1
    assert top[0].dimension_key == "color_energy"

    assert len(diffs) >= 1
    assert diffs[0].dimension_key == "structural_order"


def test_flexible_vs_priority_difference_explanation():
    """Main difference explanation includes importance level narrative."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    imp_dims = build_engine_importance_dims(priority=["color_energy"], flexible=["warmth"])

    carpet_vals = {k: 0.5 for k in CANONICAL_DIMENSIONS}
    carpet_vals["color_energy"] = 1.0  # PRIORITY mismatch
    carpet_vals["warmth"] = 1.0        # FLEXIBLE mismatch

    res = VisualStyleMatchEngine.compute_match(user_dims, imp_dims, build_engine_carpet_dims(carpet_vals))

    diff_map = {d.dimension_key: d for d in res.explanation.main_differences}
    assert "color_energy" in diff_map
    assert "öncelikli tercihlerinizden" in diff_map["color_energy"].narrative

    if "warmth" in diff_map:
        assert "esnek tercihleriniz" in diff_map["warmth"].narrative


def test_exactly_nine_dimension_records():
    """Calculated result contains exactly 9 dimension records in canonical order."""
    user_dims = build_engine_user_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})
    carpet_dims = build_engine_carpet_dims({k: 0.5 for k in CANONICAL_DIMENSIONS})

    res = VisualStyleMatchEngine.compute_match(user_dims, build_engine_importance_dims(), carpet_dims)

    assert len(res.dimensions) == 9
    assert [d.dimension_key for d in res.dimensions] == CANONICAL_DIMENSIONS


# ---------------------------------------------------------
# API INTEGRATION TESTS
# ---------------------------------------------------------

async def create_reviewed_assessment_with_importance(client: AsyncClient) -> str:
    """Helper creating assessment advanced to IMPORTANCE_COMPLETE."""
    create_res = await client.post("/api/v1/preference-assessments")
    ass_id = create_res.json()["id"]

    # 1. Text phase
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

    # 2. Visual phase
    await client.post(f"/api/v1/preference-assessments/{ass_id}/start-visual")
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

    # 3. Build & Confirm profile
    await client.post(f"/api/v1/preference-assessments/{ass_id}/build-profile")
    await client.post(f"/api/v1/preference-assessments/{ass_id}/confirm-profile")

    # 4. Importance profile
    await client.post(
        f"/api/v1/preference-assessments/{ass_id}/importance-profile",
        json={"skip": True}
    )

    return ass_id


@pytest.mark.anyio
async def test_api_extra_fields_forbidden():
    """Client sending extra fields in StyleMatchCreateRequest is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        fake_ass_id = str(uuid.uuid4())
        fake_carpet_id = str(uuid.uuid4())

        res = await client.post(
            f"/api/v1/preference-assessments/{fake_ass_id}/style-matches",
            json={
                "carpet_style_profile_id": fake_carpet_id,
                "score": 0.99  # forbidden extra field!
            }
        )
        assert res.status_code == 422


@pytest.mark.anyio
async def test_api_precondition_missing_importance():
    """Computing style match on assessment without importance profile returns 409 Conflict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create assessment without completing importance
        create_res = await client.post("/api/v1/preference-assessments")
        ass_id = create_res.json()["id"]

        fake_carpet_id = str(uuid.uuid4())

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/style-matches",
            json={"carpet_style_profile_id": fake_carpet_id}
        )
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "STYLE_MATCH_REQUIRES_IMPORTANCE_COMPLETE"


@pytest.mark.anyio
async def test_api_full_match_workflow():
    """Test end-to-end API flow: create carpet -> upload image -> style-dna -> compute style match -> GET match -> LIST matches."""
    from .factories.style_dna_images import create_d1_pair

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Carpet
        carpet_res = await client.post("/api/v1/carpets", json={"name": "Match Test Carpet"})
        assert carpet_res.status_code == 201
        carpet_id = carpet_res.json()["id"]

        # 2. Upload image
        _, img_bytes = create_d1_pair()
        img_res = await client.post(
            f"/api/v1/carpets/{carpet_id}/images",
            files={"file": ("carpet.png", img_bytes, "image/png")}
        )
        assert img_res.status_code == 201
        image_id = img_res.json()["id"]

        # 3. Compute Style DNA
        dna_res = await client.post(f"/api/v1/carpets/{carpet_id}/images/{image_id}/style-dna")
        assert dna_res.status_code == 201
        carpet_style_profile_id = dna_res.json()["id"]

        # 4. Create reviewed assessment with importance profile
        ass_id = await create_reviewed_assessment_with_importance(client)

        # 5. POST /preference-assessments/{ass_id}/style-matches
        match_req = {"carpet_style_profile_id": carpet_style_profile_id}
        match_res = await client.post(f"/api/v1/preference-assessments/{ass_id}/style-matches", json=match_req)
        assert match_res.status_code == 201
        match_data = match_res.json()

        match_id = match_data["id"]
        assert match_data["assessment_id"] == ass_id
        assert match_data["carpet_style_profile_id"] == carpet_style_profile_id
        assert match_data["match_version"] == "visual-style-match-v1"
        assert match_data["status"] in ["COMPLETE", "PARTIAL"]
        assert isinstance(match_data["score"], float)
        assert isinstance(match_data["score_100"], float)
        assert match_data["match_label"] in ["VERY_STRONG", "STRONG", "MODERATE", "LIMITED", "LOW"]
        assert len(match_data["dimensions"]) == 9
        assert "top_matches" in match_data["explanation"]

        # 6. Re-POST same request -> Idempotent response
        re_match_res = await client.post(f"/api/v1/preference-assessments/{ass_id}/style-matches", json=match_req)
        assert re_match_res.status_code in (200, 201)
        assert re_match_res.json()["id"] == match_id

        # 7. GET match by ID
        get_res = await client.get(f"/api/v1/preference-assessments/{ass_id}/style-matches/{match_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == match_id

        # 8. LIST matches for assessment
        list_res = await client.get(f"/api/v1/preference-assessments/{ass_id}/style-matches")
        assert list_res.status_code == 200
        matches_list = list_res.json()
        assert len(matches_list) == 1
        assert matches_list[0]["id"] == match_id
