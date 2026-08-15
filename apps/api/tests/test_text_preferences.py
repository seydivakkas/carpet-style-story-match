import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    TextPreferenceResponseModel,
    TextPreferenceProfileModel,
    TextPreferenceDimensionModel,
    AssessmentStatus,
    PreferenceDimensionStatus,
    TextChoiceEnum
)
from app.domain.preferences.constants import (
    TEXT_PREFERENCE_EVIDENCE_VERSION,
    CANONICAL_TEXT_QUESTIONS,
    TEXT_CHOICE_MAP,
    EVIDENCE_MATRIX_WEIGHTS
)
from app.domain.preferences.aggregator import TextPreferenceAggregator

# ---------------------------------------------------------
# UNIT TESTS (Constants, Scale Mapping, Matrix & Aggregator)
# ---------------------------------------------------------

def test_response_scale_mapping():
    assert TEXT_CHOICE_MAP[TextChoiceEnum.STRONGLY_A] == -1.00
    assert TEXT_CHOICE_MAP[TextChoiceEnum.SLIGHTLY_A] == -0.50
    assert TEXT_CHOICE_MAP[TextChoiceEnum.NEUTRAL] == 0.00
    assert TEXT_CHOICE_MAP[TextChoiceEnum.SLIGHTLY_B] == +0.50
    assert TEXT_CHOICE_MAP[TextChoiceEnum.STRONGLY_B] == +1.00

def test_canonical_questions_count_and_order():
    assert len(CANONICAL_TEXT_QUESTIONS) == 6
    expected_order = [
        "T1_ROOM_ROLE",
        "T2_COLOR_DIVERSITY",
        "T3_CONTRAST",
        "T4_WARMTH",
        "T5_STRUCTURAL_ORDER",
        "T6_FORM_LANGUAGE"
    ]
    actual_order = [q["question_key"] for q in CANONICAL_TEXT_QUESTIONS]
    assert actual_order == expected_order

def test_evidence_matrix_shape_and_t5_invariant():
    assert len(EVIDENCE_MATRIX_WEIGHTS) == 6
    for key, weights in EVIDENCE_MATRIX_WEIGHTS.items():
        assert len(weights) == 9

    # T5_STRUCTURAL_ORDER MUST NOT measure D7 (rhythm_repetition, index 6)
    t5_weights = EVIDENCE_MATRIX_WEIGHTS["T5_STRUCTURAL_ORDER"]
    assert t5_weights[6] == 0.0  # D7 rhythm_repetition
    assert t5_weights[5] == 1.0  # D6 structural_order

def test_aggregator_all_neutral():
    responses = {
        "T1_ROOM_ROLE": 0.0,
        "T2_COLOR_DIVERSITY": 0.0,
        "T3_CONTRAST": 0.0,
        "T4_WARMTH": 0.0,
        "T5_STRUCTURAL_ORDER": 0.0,
        "T6_FORM_LANGUAGE": 0.0,
    }
    dims = TextPreferenceAggregator.aggregate(responses)
    dim_map = {d["dimension_key"]: d for d in dims}

    # Measured dimensions should be 0.50
    for k in ["color_energy", "color_diversity", "contrast", "warmth", "structural_order", "focal_strength", "form_language"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.MEASURED
        assert dim_map[k]["value"] == 0.50

    # Unmeasured dimensions (D5 visual_complexity, D7 rhythm_repetition)
    for k in ["visual_complexity", "rhythm_repetition"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.NOT_MEASURED
        assert dim_map[k]["value"] is None

def test_aggregator_all_strongly_a():
    responses = {q: -1.0 for q in EVIDENCE_MATRIX_WEIGHTS.keys()}
    dims = TextPreferenceAggregator.aggregate(responses)
    dim_map = {d["dimension_key"]: d for d in dims}

    for k in ["color_energy", "color_diversity", "contrast", "warmth", "structural_order", "focal_strength", "form_language"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.MEASURED
        assert dim_map[k]["value"] == 0.00

    assert dim_map["visual_complexity"]["status"] == PreferenceDimensionStatus.NOT_MEASURED
    assert dim_map["rhythm_repetition"]["status"] == PreferenceDimensionStatus.NOT_MEASURED

def test_aggregator_all_strongly_b():
    responses = {q: +1.0 for q in EVIDENCE_MATRIX_WEIGHTS.keys()}
    dims = TextPreferenceAggregator.aggregate(responses)
    dim_map = {d["dimension_key"]: d for d in dims}

    for k in ["color_energy", "color_diversity", "contrast", "warmth", "structural_order", "focal_strength", "form_language"]:
        assert dim_map[k]["status"] == PreferenceDimensionStatus.MEASURED
        assert dim_map[k]["value"] == 1.00

    assert dim_map["visual_complexity"]["status"] == PreferenceDimensionStatus.NOT_MEASURED
    assert dim_map["rhythm_repetition"]["status"] == PreferenceDimensionStatus.NOT_MEASURED

def test_aggregator_d8_weak_secondary():
    # T1_ROOM_ROLE STRONGLY_B (+1.0)
    responses = {"T1_ROOM_ROLE": +1.0}
    dims = TextPreferenceAggregator.aggregate(responses)
    dim_map = {d["dimension_key"]: d for d in dims}

    # D8 focal_strength has weight 0.25 from T1
    assert dim_map["focal_strength"]["status"] == PreferenceDimensionStatus.MEASURED
    assert dim_map["focal_strength"]["value"] == 1.00
    assert dim_map["focal_strength"]["evidence_weight"] == 0.25
    assert dim_map["focal_strength"]["evidence_count"] == 1

def test_aggregator_d3_multi_evidence():
    # T3_CONTRAST STRONGLY_B (+1.0), T1_ROOM_ROLE STRONGLY_A (-1.0)
    # D3 weights: T3=1.0, T1=0.2
    responses = {"T3_CONTRAST": +1.0, "T1_ROOM_ROLE": -1.0}
    dims = TextPreferenceAggregator.aggregate(responses)
    dim_map = {d["dimension_key"]: d for d in dims}

    # Weighted avg = (+1.0*1.0 + -1.0*0.2) / (1.2) = 0.8 / 1.2 = +0.6667
    # Pref value = (+0.6667 + 1) / 2 = 0.8333
    assert dim_map["contrast"]["status"] == PreferenceDimensionStatus.MEASURED
    assert dim_map["contrast"]["value"] == 0.8333
    assert dim_map["contrast"]["evidence_weight"] == 1.20
    assert dim_map["contrast"]["evidence_count"] == 2

# ---------------------------------------------------------
# API & INTEGRATION TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_get_meta_preference_questions(client: AsyncClient):
    resp = await client.get("/api/v1/meta/preference-text-questions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_questions"] == 6
    assert len(data["questions"]) == 6
    assert data["questions"][0]["question_key"] == "T1_ROOM_ROLE"
    assert data["questions"][5]["question_key"] == "T6_FORM_LANGUAGE"

@pytest.mark.asyncio
async def test_text_preference_assessment_lifecycle(client: AsyncClient):
    # 1. Create Assessment -> 201 Created
    create_resp = await client.post("/api/v1/preference-assessments")
    assert create_resp.status_code == 201
    assessment_data = create_resp.json()
    assessment_id = assessment_data["id"]
    assert assessment_data["status"] == "TEXT_PENDING"
    assert assessment_data["evidence_version"] == TEXT_PREFERENCE_EVIDENCE_VERSION

    # 2. Try completing before answering all 6 -> 409 Conflict
    incomplete_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    assert incomplete_resp.status_code == 409
    err = incomplete_resp.json()
    assert err["detail"]["code"] == "TEXT_PREFERENCES_INCOMPLETE"
    assert err["detail"]["answered_count"] == 0
    assert len(err["detail"]["missing_keys"]) == 6

    # 3. Answer 5 questions
    choices = ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    q_keys = ["T1_ROOM_ROLE", "T2_COLOR_DIVERSITY", "T3_CONTRAST", "T4_WARMTH", "T5_STRUCTURAL_ORDER"]

    for q_key, choice in zip(q_keys, choices):
        put_resp = await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}",
            json={"choice": choice}
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["question_key"] == q_key
        assert put_resp.json()["choice"] == choice

    # Verify answers list
    get_resps = await client.get(f"/api/v1/preference-assessments/{assessment_id}/text-responses")
    assert get_resps.status_code == 200
    assert len(get_resps.json()) == 5

    # 4. Answer 6th question (T6_FORM_LANGUAGE)
    await client.put(
        f"/api/v1/preference-assessments/{assessment_id}/text-responses/T6_FORM_LANGUAGE",
        json={"choice": "NEUTRAL"}
    )

    # 5. Complete text assessment -> 200 OK
    complete_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
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

    # Check unmeasured D5 & D7
    dim_map = {d["key"]: d for d in profile_data["dimensions"]}
    assert dim_map["visual_complexity"]["status"] == "NOT_MEASURED"
    assert dim_map["visual_complexity"]["value"] is None
    assert dim_map["rhythm_repetition"]["status"] == "NOT_MEASURED"
    assert dim_map["rhythm_repetition"]["value"] is None

    # Check assessment status updated to TEXT_COMPLETE
    status_resp = await client.get(f"/api/v1/preference-assessments/{assessment_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "TEXT_COMPLETE"

    # 6. Completed Assessment Immutability Lock -> PUT fails with 409
    locked_resp = await client.put(
        f"/api/v1/preference-assessments/{assessment_id}/text-responses/T1_ROOM_ROLE",
        json={"choice": "STRONGLY_B"}
    )
    assert locked_resp.status_code == 409
    assert locked_resp.json()["detail"]["code"] == "TEXT_PREFERENCES_ALREADY_COMPLETED"

    # 7. Idempotent complete re-POST -> 200 OK
    re_complete_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    assert re_complete_resp.status_code == 200
    assert re_complete_resp.json()["id"] == profile_data["id"]

    # 8. GET text-profile -> 200 OK
    get_profile_resp = await client.get(f"/api/v1/preference-assessments/{assessment_id}/text-profile")
    assert get_profile_resp.status_code == 200
    assert get_profile_resp.json()["id"] == profile_data["id"]

@pytest.mark.asyncio
async def test_text_preference_cascade_delete(client: AsyncClient, db_session: AsyncSession):
    # Create & complete assessment
    create_resp = await client.post("/api/v1/preference-assessments")
    assessment_id = create_resp.json()["id"]

    for q_key in ["T1_ROOM_ROLE", "T2_COLOR_DIVERSITY", "T3_CONTRAST", "T4_WARMTH", "T5_STRUCTURAL_ORDER", "T6_FORM_LANGUAGE"]:
        await client.put(
            f"/api/v1/preference-assessments/{assessment_id}/text-responses/{q_key}",
            json={"choice": "NEUTRAL"}
        )

    comp_resp = await client.post(f"/api/v1/preference-assessments/{assessment_id}/complete-text")
    profile_id = uuid.UUID(comp_resp.json()["id"])
    assessment_uuid = uuid.UUID(assessment_id)

    # Delete assessment directly from session
    assessment_obj = await db_session.get(PreferenceAssessmentModel, assessment_uuid)
    await db_session.delete(assessment_obj)
    await db_session.commit()

    # Verify responses, profile, and dimensions deleted
    prof = await db_session.get(TextPreferenceProfileModel, profile_id)
    assert prof is None
