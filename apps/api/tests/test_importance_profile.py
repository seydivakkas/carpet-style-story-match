import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.preferences.builder import ImportanceProfileBuilder
from app.db.models.preference_assessment import (
    ImportanceLevelEnum,
    ImportanceCompletionModeEnum
)
from app.domain.preferences.exceptions import (
    ImportanceSelectionTooManyPriorityError,
    ImportanceSelectionTooManyFlexibleError,
    ImportanceSelectionOverlapError,
    ImportanceSelectionDuplicateError,
    ImportanceSelectionUnknownDimensionError,
    ImportanceSelectionInvalidSkipError,
    ImportanceSelectionEmptyError
)

# Helper to create and advance assessment to PROFILE_REVIEWED status
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


@pytest.mark.anyio
async def test_builder_unit_rules():
    # 1. Skip
    mode, dims = ImportanceProfileBuilder.build(skip=True, priority_dimensions=[], flexible_dimensions=[])
    assert mode == ImportanceCompletionModeEnum.SKIPPED_ALL_STANDARD
    assert len(dims) == 9
    assert all(d["level"] == ImportanceLevelEnum.STANDARD and d["weight"] == 0.60 for d in dims)

    # 2. Invalid skip
    with pytest.raises(ImportanceSelectionInvalidSkipError):
        ImportanceProfileBuilder.build(skip=True, priority_dimensions=["color_energy"], flexible_dimensions=[])

    # 3. Empty explicit
    with pytest.raises(ImportanceSelectionEmptyError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=[], flexible_dimensions=[])

    # 4. Too many priority
    with pytest.raises(ImportanceSelectionTooManyPriorityError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=["color_energy", "color_diversity", "contrast", "warmth"], flexible_dimensions=[])

    # 5. Too many flexible
    with pytest.raises(ImportanceSelectionTooManyFlexibleError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=[], flexible_dimensions=["color_energy", "color_diversity", "contrast", "warmth"])

    # 6. Duplicate
    with pytest.raises(ImportanceSelectionDuplicateError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=["contrast", "contrast"], flexible_dimensions=[])

    # 7. Overlap
    with pytest.raises(ImportanceSelectionOverlapError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=["contrast"], flexible_dimensions=["contrast"])

    # 8. Unknown
    with pytest.raises(ImportanceSelectionUnknownDimensionError):
        ImportanceProfileBuilder.build(skip=False, priority_dimensions=["beauty"], flexible_dimensions=[])


@pytest.mark.anyio
async def test_importance_profile_default_skip_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": True}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["completion_mode"] == "SKIPPED_ALL_STANDARD"
        assert data["importance_version"] == "importance-v1"
        assert len(data["dimensions"]) == 9

        for dim in data["dimensions"]:
            assert dim["level"] == "STANDARD"
            assert dim["weight"] == 0.60

        # Check assessment status transition
        ass_res = await client.get(f"/api/v1/preference-assessments/{ass_id}")
        assert ass_res.json()["status"] == "IMPORTANCE_COMPLETE"


@pytest.mark.anyio
async def test_importance_profile_priority_selection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={
                "skip": False,
                "priority_dimensions": ["color_energy", "form_language"],
                "flexible_dimensions": []
            }
        )
        assert res.status_code == 201
        data = res.json()
        assert data["completion_mode"] == "EXPLICIT_SELECTION"
        dim_map = {d["dimension_key"]: d for d in data["dimensions"]}

        assert dim_map["color_energy"]["level"] == "PRIORITY"
        assert dim_map["color_energy"]["weight"] == 1.00

        assert dim_map["form_language"]["level"] == "PRIORITY"
        assert dim_map["form_language"]["weight"] == 1.00

        # Remaining 7 standard
        assert dim_map["contrast"]["level"] == "STANDARD"
        assert dim_map["contrast"]["weight"] == 0.60


@pytest.mark.anyio
async def test_importance_profile_flexible_selection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={
                "skip": False,
                "priority_dimensions": [],
                "flexible_dimensions": ["warmth", "focal_strength"]
            }
        )
        assert res.status_code == 201
        data = res.json()
        dim_map = {d["dimension_key"]: d for d in data["dimensions"]}

        assert dim_map["warmth"]["level"] == "FLEXIBLE"
        assert dim_map["warmth"]["weight"] == 0.25

        assert dim_map["focal_strength"]["level"] == "FLEXIBLE"
        assert dim_map["focal_strength"]["weight"] == 0.25

        assert dim_map["color_energy"]["level"] == "STANDARD"
        assert dim_map["color_energy"]["weight"] == 0.60


@pytest.mark.anyio
async def test_importance_profile_mixed_selection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={
                "skip": False,
                "priority_dimensions": ["color_energy", "structural_order", "form_language"],
                "flexible_dimensions": ["color_diversity", "warmth", "focal_strength"]
            }
        )
        assert res.status_code == 201
        data = res.json()
        dims = data["dimensions"]

        p_count = sum(1 for d in dims if d["level"] == "PRIORITY")
        f_count = sum(1 for d in dims if d["level"] == "FLEXIBLE")
        s_count = sum(1 for d in dims if d["level"] == "STANDARD")

        assert p_count == 3
        assert f_count == 3
        assert s_count == 3


@pytest.mark.anyio
async def test_importance_selection_validation_errors():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        # Too many priority -> 422
        res1 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "priority_dimensions": ["color_energy", "color_diversity", "contrast", "warmth"]}
        )
        assert res1.status_code == 422
        assert res1.json()["detail"]["code"] == "IMPORTANCE_TOO_MANY_PRIORITY"

        # Too many flexible -> 422
        res2 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "flexible_dimensions": ["color_energy", "color_diversity", "contrast", "warmth"]}
        )
        assert res2.status_code == 422
        assert res2.json()["detail"]["code"] == "IMPORTANCE_TOO_MANY_FLEXIBLE"

        # Overlap -> 422
        res3 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "priority_dimensions": ["contrast"], "flexible_dimensions": ["contrast"]}
        )
        assert res3.status_code == 422
        assert res3.json()["detail"]["code"] == "IMPORTANCE_SELECTION_OVERLAP"

        # Duplicate -> 422
        res4 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "priority_dimensions": ["contrast", "contrast"]}
        )
        assert res4.status_code == 422
        assert res4.json()["detail"]["code"] == "IMPORTANCE_SELECTION_DUPLICATE"

        # Unknown dimension -> 422
        res5 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "priority_dimensions": ["beauty"]}
        )
        assert res5.status_code == 422
        assert res5.json()["detail"]["code"] == "IMPORTANCE_SELECTION_UNKNOWN_DIMENSION"

        # Invalid skip -> 422
        res6 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": True, "priority_dimensions": ["contrast"]}
        )
        assert res6.status_code == 422
        assert res6.json()["detail"]["code"] == "IMPORTANCE_SELECTION_INVALID_SKIP"

        # Empty explicit -> 422
        res7 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": False, "priority_dimensions": [], "flexible_dimensions": []}
        )
        assert res7.status_code == 422
        assert res7.json()["detail"]["code"] == "IMPORTANCE_SELECTION_EMPTY"


@pytest.mark.anyio
async def test_precondition_requires_reviewed_profile():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create assessment and stop before review
        create_res = await client.post("/api/v1/preference-assessments")
        ass_id = create_res.json()["id"]

        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": True}
        )
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "IMPORTANCE_REQUIRES_REVIEWED_PREFERENCE_PROFILE"


@pytest.mark.anyio
async def test_profile_independence_and_no_confidence_influence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        # Get preference & confidence profiles BEFORE importance creation
        pref_before = (await client.get(f"/api/v1/preference-assessments/{ass_id}/preference-profile")).json()
        conf_before = (await client.get(f"/api/v1/preference-assessments/{ass_id}/confidence-profile")).json()

        # D8 focal_strength confidence is 0.15 (low)
        d8_conf_val = next(d for d in conf_before["dimensions"] if d["dimension_key"] == "focal_strength")["confidence"]
        assert d8_conf_val == 0.15

        # Create Importance: Select low-confidence D8 as PRIORITY (1.00), high-confidence D1 as FLEXIBLE (0.25)
        imp_res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={
                "skip": False,
                "priority_dimensions": ["focal_strength"],
                "flexible_dimensions": ["color_energy"]
            }
        )
        assert imp_res.status_code == 201
        imp_data = imp_res.json()
        imp_map = {d["dimension_key"]: d for d in imp_data["dimensions"]}

        # Low-confidence D8 gets full 1.00 weight without reduction!
        assert imp_map["focal_strength"]["level"] == "PRIORITY"
        assert imp_map["focal_strength"]["weight"] == 1.00

        # High-confidence D1 gets 0.25 weight
        assert imp_map["color_energy"]["level"] == "FLEXIBLE"
        assert imp_map["color_energy"]["weight"] == 0.25

        # Get preference & confidence profiles AFTER importance creation -> UNCHANGED!
        pref_after = (await client.get(f"/api/v1/preference-assessments/{ass_id}/preference-profile")).json()
        conf_after = (await client.get(f"/api/v1/preference-assessments/{ass_id}/confidence-profile")).json()

        assert pref_before == pref_after
        assert conf_before == conf_after


@pytest.mark.anyio
async def test_server_owned_weights_extra_forbid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        # Try passing custom weights field -> 422 Validation Error
        res = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={
                "skip": False,
                "priority_dimensions": ["color_energy"],
                "weights": {"color_energy": 0.99}
            }
        )
        assert res.status_code == 422


@pytest.mark.anyio
async def test_idempotency_and_conflict():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ass_id = await create_reviewed_assessment(client)

        req_data = {
            "skip": False,
            "priority_dimensions": ["color_energy"],
            "flexible_dimensions": ["warmth"]
        }

        # 1. Create first time
        res1 = await client.post(f"/api/v1/preference-assessments/{ass_id}/importance-profile", json=req_data)
        assert res1.status_code == 201
        prof_id = res1.json()["id"]

        # 2. Post exact same request again -> Returns existing profile (Idempotent 200/201)
        res2 = await client.post(f"/api/v1/preference-assessments/{ass_id}/importance-profile", json=req_data)
        assert res2.status_code in (200, 201)
        assert res2.json()["id"] == prof_id

        # 3. Post DIFFERENT request -> 409 Conflict
        res3 = await client.post(
            f"/api/v1/preference-assessments/{ass_id}/importance-profile",
            json={"skip": True}
        )
        assert res3.status_code == 409
        assert res3.json()["detail"]["code"] == "IMPORTANCE_PROFILE_ALREADY_EXISTS"

        # 4. GET Importance Profile
        get_res = await client.get(f"/api/v1/preference-assessments/{ass_id}/importance-profile")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == prof_id


@pytest.mark.anyio
async def test_meta_importance_profile_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/meta/importance-profile")
        assert res.status_code == 200
        data = res.json()

        assert data["version"] == "importance-v1"
        assert data["max_priority"] == 3
        assert data["max_flexible"] == 3
        assert data["weights"]["PRIORITY"] == 1.00
        assert data["weights"]["STANDARD"] == 0.60
        assert data["weights"]["FLEXIBLE"] == 0.25
        assert len(data["canonical_dimensions"]) == 9
