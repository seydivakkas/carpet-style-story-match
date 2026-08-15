import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel,
    StyleProfileStatus,
    StyleDimensionStatus
)
from app.domain.styledna.engine import StyleDNAEngine, STYLE_DNA_ALGORITHM_VERSION
from .factories.style_dna_images import (
    create_d1_pair,
    create_d2_pair,
    create_d3_pair,
    create_d4_pair,
    create_d5_pair,
    create_d6_pair,
    create_d7_pair,
    create_d6_d7_quadrants,
    create_d8_triplet,
    create_d9_pair,
    create_blank_image
)

# ---------------------------------------------------------
# ENGINE UNIT TESTS (Relative benchmarks & Invariants)
# ---------------------------------------------------------

def test_engine_d1_color_energy():
    engine = StyleDNAEngine()
    low_bytes, high_bytes = create_d1_pair()

    _, dims_low = engine.analyze(low_bytes)
    _, dims_high = engine.analyze(high_bytes)

    d1_low = next(d for d in dims_low if d["key"] == "color_energy")
    d1_high = next(d for d in dims_high if d["key"] == "color_energy")

    assert d1_high["value"] > d1_low["value"]
    assert d1_high["status"] == StyleDimensionStatus.AVAILABLE

def test_engine_d2_color_diversity():
    engine = StyleDNAEngine()
    bytes2, bytes8 = create_d2_pair()

    _, dims2 = engine.analyze(bytes2)
    _, dims8 = engine.analyze(bytes8)

    d2_2 = next(d for d in dims2 if d["key"] == "color_diversity")
    d2_8 = next(d for d in dims8 if d["key"] == "color_diversity")

    assert d2_8["value"] > d2_2["value"]

def test_engine_d3_contrast():
    engine = StyleDNAEngine()
    low_bytes, high_bytes = create_d3_pair()

    _, dims_low = engine.analyze(low_bytes)
    _, dims_high = engine.analyze(high_bytes)

    d3_low = next(d for d in dims_low if d["key"] == "contrast")
    d3_high = next(d for d in dims_high if d["key"] == "contrast")

    assert d3_high["value"] > d3_low["value"]

def test_engine_d4_warmth():
    engine = StyleDNAEngine()
    cool_bytes, warm_bytes = create_d4_pair()

    _, dims_cool = engine.analyze(cool_bytes)
    _, dims_warm = engine.analyze(warm_bytes)

    d4_cool = next(d for d in dims_cool if d["key"] == "warmth")
    d4_warm = next(d for d in dims_warm if d["key"] == "warmth")

    assert d4_cool["value"] < 0.4
    assert d4_warm["value"] > 0.6
    assert d4_warm["value"] > d4_cool["value"]

def test_engine_d5_visual_complexity():
    engine = StyleDNAEngine()
    simple_bytes, detailed_bytes = create_d5_pair()

    _, dims_simple = engine.analyze(simple_bytes)
    _, dims_detailed = engine.analyze(detailed_bytes)

    d5_simple = next(d for d in dims_simple if d["key"] == "visual_complexity")
    d5_detailed = next(d for d in dims_detailed if d["key"] == "visual_complexity")

    assert d5_detailed["value"] > d5_simple["value"]

def test_engine_d6_structural_order():
    engine = StyleDNAEngine()
    asym_bytes, sym_bytes = create_d6_pair()

    _, dims_asym = engine.analyze(asym_bytes)
    _, dims_sym = engine.analyze(sym_bytes)

    d6_asym = next(d for d in dims_asym if d["key"] == "structural_order")
    d6_sym = next(d for d in dims_sym if d["key"] == "structural_order")

    assert d6_sym["value"] > d6_asym["value"]

def test_engine_d7_rhythm_repetition():
    engine = StyleDNAEngine()
    single_bytes, repeated_bytes = create_d7_pair()

    _, dims_single = engine.analyze(single_bytes)
    _, dims_repeated = engine.analyze(repeated_bytes)

    d7_single = next(d for d in dims_single if d["key"] == "rhythm_repetition")
    d7_repeated = next(d for d in dims_repeated if d["key"] == "rhythm_repetition")

    assert d7_repeated["value"] > d7_single["value"]

def test_engine_d6_d7_quadrant_tests():
    engine = StyleDNAEngine()
    quads = create_d6_d7_quadrants()

    res = {}
    for q_name, q_bytes in quads.items():
        _, dims = engine.analyze(q_bytes)
        d6 = next(d for d in dims if d["key"] == "structural_order")["value"]
        d7 = next(d for d in dims if d["key"] == "rhythm_repetition")["value"]
        res[q_name] = (d6, d7)

    # Q1: High Order, Low Repetition
    # Q2: Low Order, High Repetition
    # Q3: High Order, High Repetition
    # Q4: Low Order, Low Repetition
    assert res["Q1"][0] > res["Q4"][0]  # Q1 order > Q4 order
    assert res["Q3"][1] > res["Q1"][1]  # Q3 rep > Q1 rep
    assert res["Q3"][0] > res["Q2"][0]  # Q3 order > Q2 order

def test_engine_d8_focal_strength():
    engine = StyleDNAEngine()
    uniform_b, central_b, offcenter_b = create_d8_triplet()

    _, dims_uni = engine.analyze(uniform_b)
    _, dims_cen = engine.analyze(central_b)
    _, dims_off = engine.analyze(offcenter_b)

    d8_uni = next(d for d in dims_uni if d["key"] == "focal_strength")["value"]
    d8_cen = next(d for d in dims_cen if d["key"] == "focal_strength")["value"]
    d8_off = next(d for d in dims_off if d["key"] == "focal_strength")["value"]

    assert d8_cen > d8_uni
    assert d8_off > d8_uni

def test_engine_d9_form_language():
    engine = StyleDNAEngine()
    geom_bytes, organic_bytes = create_d9_pair()

    _, dims_geom = engine.analyze(geom_bytes)
    _, dims_organic = engine.analyze(organic_bytes)

    d9_geom = next(d for d in dims_geom if d["key"] == "form_language")["value"]
    d9_organic = next(d for d in dims_organic if d["key"] == "form_language")["value"]

    assert d9_organic > d9_geom

def test_engine_blank_image_handling():
    engine = StyleDNAEngine()
    blank_bytes = create_blank_image()

    status, dims = engine.analyze(blank_bytes)
    d9 = next(d for d in dims if d["key"] == "form_language")

    assert d9["status"] == StyleDimensionStatus.NOT_AVAILABLE
    assert d9["value"] is None

def test_engine_determinism():
    engine = StyleDNAEngine()
    test_bytes, _ = create_d1_pair()

    status1, dims1 = engine.analyze(test_bytes)
    status2, dims2 = engine.analyze(test_bytes)

    assert status1 == status2
    for d1, d2 in zip(dims1, dims2):
        assert d1["key"] == d2["key"]
        assert d1["value"] == pytest.approx(d2["value"], abs=1e-6)
        assert d1["confidence"] == pytest.approx(d2["confidence"], abs=1e-6)
        assert d1["status"] == d2["status"]

def test_engine_value_ranges():
    engine = StyleDNAEngine()
    test_bytes, _ = create_d1_pair()
    _, dims = engine.analyze(test_bytes)

    for d in dims:
        if d["value"] is not None:
            assert 0.0 <= d["value"] <= 1.0
        assert 0.0 <= d["confidence"] <= 1.0

# ---------------------------------------------------------
# API & INTEGRATION TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_and_get_style_dna_api(client: AsyncClient):
    # 1. Create carpet
    resp = await client.post(
        "/api/v1/carpets",
        json={"name": "Style DNA Test Carpet"}
    )
    assert resp.status_code == 201
    carpet_id = resp.json()["id"]

    # 2. Upload valid image
    _, img_bytes = create_d1_pair()
    resp = await client.post(
        f"/api/v1/carpets/{carpet_id}/images",
        files={"file": ("vivid.png", img_bytes, "image/png")}
    )
    assert resp.status_code == 201
    image_id = resp.json()["id"]

    # 3. POST style-dna (Calculate & Persist) -> 201 Created
    resp = await client.post(f"/api/v1/carpets/{carpet_id}/images/{image_id}/style-dna")
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["carpet_id"] == carpet_id
    assert data["image_id"] == image_id
    assert data["algorithm_version"] == STYLE_DNA_ALGORITHM_VERSION
    assert len(data["dimensions"]) == 9

    # Canonical dimension key order check
    expected_keys = [
        "color_energy", "color_diversity", "contrast", "warmth",
        "visual_complexity", "structural_order", "rhythm_repetition",
        "focal_strength", "form_language"
    ]
    actual_keys = [d["key"] for d in data["dimensions"]]
    assert actual_keys == expected_keys

    # 4. Idempotent re-POST -> 200 OK
    resp_reused = await client.post(f"/api/v1/carpets/{carpet_id}/images/{image_id}/style-dna")
    assert resp_reused.status_code == 200
    assert resp_reused.json()["id"] == data["id"]

    # 5. GET style-dna -> 200 OK
    resp_get = await client.get(f"/api/v1/carpets/{carpet_id}/images/{image_id}/style-dna")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == data["id"]

@pytest.mark.asyncio
async def test_style_dna_cascade_delete(client: AsyncClient, db_session: AsyncSession):
    # Create carpet & image
    resp = await client.post("/api/v1/carpets", json={"name": "Cascade Test Carpet"})
    carpet_id = resp.json()["id"]

    _, img_bytes = create_d1_pair()
    resp = await client.post(
        f"/api/v1/carpets/{carpet_id}/images",
        files={"file": ("test.png", img_bytes, "image/png")}
    )
    image_id = resp.json()["id"]

    # Calculate style-dna
    resp = await client.post(f"/api/v1/carpets/{carpet_id}/images/{image_id}/style-dna")
    assert resp.status_code == 201
    profile_id = uuid.UUID(resp.json()["id"])

    # Delete image
    resp = await client.delete(f"/api/v1/carpets/{carpet_id}/images/{image_id}")
    assert resp.status_code == 204

    # Verify DB profile and dimensions deleted
    stmt = select(CarpetStyleProfileModel).where(CarpetStyleProfileModel.id == profile_id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None
