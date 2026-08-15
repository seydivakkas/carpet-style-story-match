"""Comprehensive test suite for User Narrative Profile v1."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    AssessmentStatus,
    UserProfileStatusEnum,
    UserPreferenceProfileModel,
    NarrativeInterestLevelEnum,
    NarrativeCompletionModeEnum,
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES as CONTRACT_NARRATIVE_THEMES
from app.domain.narrative.constants import (
    USER_NARRATIVE_PROFILE_VERSION,
    CANONICAL_NARRATIVE_THEMES,
    INTEREST_LEVEL_WEIGHTS,
)
from app.domain.narrative.builder import NarrativeProfileBuilder
from app.domain.narrative.exceptions import (
    NarrativeSelectionEmptyError,
    NarrativeSelectionOverlapError,
    NarrativeSelectionDuplicateError,
    NarrativeSelectionTooManyPrimaryError,
    NarrativeSelectionTooManySecondaryError,
    NarrativeSelectionUnknownThemeError,
    NarrativeSkipConflictError,
)


# Helper to advance an assessment to REVIEWED status via API
async def create_reviewed_assessment(client: AsyncClient) -> str:
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

    return ass_id


# 1. Exact Theme Contract Test
def test_exact_theme_contract():
    assert len(CANONICAL_NARRATIVE_THEMES) == 8
    assert [t["key"] for t in CONTRACT_NARRATIVE_THEMES] == CANONICAL_NARRATIVE_THEMES
    expected = [
        "nature_growth",
        "belonging_home",
        "journey_discovery",
        "continuity_connection",
        "balance_order",
        "renewal_transformation",
        "tradition_craft",
        "cultural_heritage",
    ]
    assert CANONICAL_NARRATIVE_THEMES == expected


# 2. Level Mapping Test
def test_level_mapping():
    assert INTEREST_LEVEL_WEIGHTS["PRIMARY"] == 1.00
    assert INTEREST_LEVEL_WEIGHTS["SECONDARY"] == 0.60
    assert INTEREST_LEVEL_WEIGHTS["NOT_SELECTED"] == 0.00


# 3. Basic Profile Builder Test
def test_basic_profile_builder():
    built = NarrativeProfileBuilder.build(
        skip=False,
        primary_themes=["tradition_craft", "cultural_heritage"],
        secondary_themes=["continuity_connection"]
    )
    assert built.completion_mode == NarrativeCompletionModeEnum.EXPLICIT_SELECTION
    assert len(built.themes) == 8

    theme_map = {item.theme_key: item for item in built.themes}
    assert theme_map["tradition_craft"].interest_level == NarrativeInterestLevelEnum.PRIMARY
    assert theme_map["tradition_craft"].interest_weight == 1.00

    assert theme_map["cultural_heritage"].interest_level == NarrativeInterestLevelEnum.PRIMARY
    assert theme_map["cultural_heritage"].interest_weight == 1.00

    assert theme_map["continuity_connection"].interest_level == NarrativeInterestLevelEnum.SECONDARY
    assert theme_map["continuity_connection"].interest_weight == 0.60

    for key in ["nature_growth", "belonging_home", "journey_discovery", "balance_order", "renewal_transformation"]:
        assert theme_map[key].interest_level == NarrativeInterestLevelEnum.NOT_SELECTED
        assert theme_map[key].interest_weight == 0.00


# 4. Skip Builder Test
def test_skip_builder():
    built = NarrativeProfileBuilder.build(
        skip=True,
        primary_themes=[],
        secondary_themes=[]
    )
    assert built.completion_mode == NarrativeCompletionModeEnum.SKIPPED
    assert len(built.themes) == 8
    for item in built.themes:
        assert item.interest_level == NarrativeInterestLevelEnum.NOT_SELECTED
        assert item.interest_weight == 0.00


# 5. Skip Does Not Mean Dislike Test
def test_skip_does_not_mean_dislike():
    for member in NarrativeInterestLevelEnum:
        assert member.value not in ["DISLIKE", "REJECTED", "NEGATIVE"]


# 6. Builder Validation Errors
def test_builder_validation_errors():
    # Empty
    with pytest.raises(NarrativeSelectionEmptyError):
        NarrativeProfileBuilder.build(skip=False, primary_themes=[], secondary_themes=[])

    # Too many primary
    with pytest.raises(NarrativeSelectionTooManyPrimaryError):
        NarrativeProfileBuilder.build(
            skip=False,
            primary_themes=["nature_growth", "belonging_home", "journey_discovery", "balance_order"],
            secondary_themes=[]
        )

    # Too many secondary
    with pytest.raises(NarrativeSelectionTooManySecondaryError):
        NarrativeProfileBuilder.build(
            skip=False,
            primary_themes=[],
            secondary_themes=["nature_growth", "belonging_home", "journey_discovery", "balance_order"]
        )

    # Overlap
    with pytest.raises(NarrativeSelectionOverlapError):
        NarrativeProfileBuilder.build(
            skip=False,
            primary_themes=["nature_growth"],
            secondary_themes=["nature_growth"]
        )

    # Duplicate
    with pytest.raises(NarrativeSelectionDuplicateError):
        NarrativeProfileBuilder.build(
            skip=False,
            primary_themes=["nature_growth", "nature_growth"],
            secondary_themes=[]
        )

    # Unknown
    with pytest.raises(NarrativeSelectionUnknownThemeError):
        NarrativeProfileBuilder.build(
            skip=False,
            primary_themes=["success"],
            secondary_themes=[]
        )

    # Skip conflict
    with pytest.raises(NarrativeSkipConflictError):
        NarrativeProfileBuilder.build(
            skip=True,
            primary_themes=["nature_growth"],
            secondary_themes=[]
        )


# 7. Zero Primary Allowed
def test_zero_primary_allowed():
    built = NarrativeProfileBuilder.build(
        skip=False,
        primary_themes=[],
        secondary_themes=["journey_discovery"]
    )
    assert built.completion_mode == NarrativeCompletionModeEnum.EXPLICIT_SELECTION
    theme_map = {item.theme_key: item for item in built.themes}
    assert theme_map["journey_discovery"].interest_level == NarrativeInterestLevelEnum.SECONDARY


# Async API Tests
@pytest.mark.asyncio
async def test_narrative_profile_lifecycle_api(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    payload = {
        "skip": False,
        "primary_themes": ["tradition_craft", "cultural_heritage"],
        "secondary_themes": ["continuity_connection"]
    }

    res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json=payload
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["profile_version"] == USER_NARRATIVE_PROFILE_VERSION
    assert data["completion_mode"] == "EXPLICIT_SELECTION"
    assert len(data["themes"]) == 8

    # Verify canonical order
    keys = [t["key"] for t in data["themes"]]
    assert keys == CANONICAL_NARRATIVE_THEMES

    # Get narrative profile
    get_res = await client.get(f"/api/v1/preference-assessments/{ass_id}/narrative-profile")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_exactly_8_persisted_rows(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["nature_growth"], "secondary_themes": []}
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["themes"]) == 8


@pytest.mark.asyncio
async def test_skip_api(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": True, "primary_themes": [], "secondary_themes": []}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["completion_mode"] == "SKIPPED"
    for theme in data["themes"]:
        assert theme["interest_level"] == "NOT_SELECTED"
        assert theme["interest_weight"] == 0.0


@pytest.mark.asyncio
async def test_precondition_requires_reviewed_profile(client: AsyncClient):
    create_res = await client.post("/api/v1/preference-assessments")
    ass_id = create_res.json()["id"]

    res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["nature_growth"], "secondary_themes": []}
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NARRATIVE_PROFILE_REQUIRES_REVIEWED_PREFERENCE_PROFILE"


@pytest.mark.asyncio
async def test_importance_independence(client: AsyncClient):
    """Narrative profile creation MUST succeed even when ImportanceProfile does NOT exist."""
    ass_id = await create_reviewed_assessment(client)

    # Verify NO importance profile exists yet
    get_imp = await client.get(f"/api/v1/preference-assessments/{ass_id}/importance-profile")
    assert get_imp.status_code == 404

    res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["tradition_craft"], "secondary_themes": []}
    )
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_assessment_status_unchanged(client: AsyncClient):
    """Creating narrative profile MUST NOT change assessment.status (e.g. IMPORTANCE_COMPLETE stays IMPORTANCE_COMPLETE)."""
    ass_id = await create_reviewed_assessment(client)

    # Complete importance phase first
    imp_res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/importance-profile",
        json={"skip": True, "priority_dimensions": [], "flexible_dimensions": []}
    )
    assert imp_res.status_code == 201

    ass_after_imp = await client.get(f"/api/v1/preference-assessments/{ass_id}")
    assert ass_after_imp.json()["status"] == "IMPORTANCE_COMPLETE"

    # Create narrative profile
    nar_res = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["nature_growth"], "secondary_themes": []}
    )
    assert nar_res.status_code == 201

    # Status must STILL be IMPORTANCE_COMPLETE
    ass_after_nar = await client.get(f"/api/v1/preference-assessments/{ass_id}")
    assert ass_after_nar.json()["status"] == "IMPORTANCE_COMPLETE"


@pytest.mark.asyncio
async def test_idempotency_and_conflict(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    payload = {"skip": False, "primary_themes": ["nature_growth"], "secondary_themes": ["belonging_home"]}

    # First request -> 201
    res1 = await client.post(f"/api/v1/preference-assessments/{ass_id}/narrative-profile", json=payload)
    assert res1.status_code == 201

    # Exact same second request -> Idempotent 201
    res2 = await client.post(f"/api/v1/preference-assessments/{ass_id}/narrative-profile", json=payload)
    assert res2.status_code == 201
    assert res2.json()["id"] == res1.json()["id"]

    # Different second request -> 409
    payload_diff = {"skip": False, "primary_themes": ["journey_discovery"], "secondary_themes": []}
    res3 = await client.post(f"/api/v1/preference-assessments/{ass_id}/narrative-profile", json=payload_diff)
    assert res3.status_code == 409
    assert res3.json()["detail"]["code"] == "NARRATIVE_PROFILE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_extra_fields_forbidden(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    # Try setting client weight
    payload = {"skip": False, "primary_themes": ["nature_growth"], "secondary_themes": [], "interest_weight": 1.0}
    res = await client.post(f"/api/v1/preference-assessments/{ass_id}/narrative-profile", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_meta_narrative_profile_endpoint(client: AsyncClient):
    res = await client.get("/api/v1/meta/narrative-profile")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == USER_NARRATIVE_PROFILE_VERSION
    assert data["levels"] == {"PRIMARY": 1.0, "SECONDARY": 0.6, "NOT_SELECTED": 0.0}
    assert data["max_primary"] == 3
    assert data["max_secondary"] == 3
    assert data["skip_supported"] is True


@pytest.mark.asyncio
async def test_canonical_key_contract_validation(client: AsyncClient):
    ass_id = await create_reviewed_assessment(client)

    # Sending presentation code N3_JOURNEY_DISCOVERY must be rejected with 422 UNPROCESSABLE_ENTITY
    res_bad = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["N3_JOURNEY_DISCOVERY"], "secondary_themes": []}
    )
    assert res_bad.status_code == 422
    assert res_bad.json()["detail"]["code"] == "NARRATIVE_SELECTION_UNKNOWN_THEME"

    # Sending canonical key journey_discovery must succeed
    res_good = await client.post(
        f"/api/v1/preference-assessments/{ass_id}/narrative-profile",
        json={"skip": False, "primary_themes": ["journey_discovery"], "secondary_themes": ["continuity_connection"]}
    )
    assert res_good.status_code == 201
    theme_keys = [t["key"] for t in res_good.json()["themes"]]
    assert "journey_discovery" in theme_keys
    assert "N3_JOURNEY_DISCOVERY" not in theme_keys

