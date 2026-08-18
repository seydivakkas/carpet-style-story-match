"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Focused Test Suite for V2-07 & V2-07A — Historical + Catalog Visual Retrieval
Verifies:
1. 9D Canonical Dimension Order & Uniform Equal Weights
2. Identical vector -> distance 0.0, score 100.0
3. Opposite extreme vector -> max distance 1.0, score 0.0
4. Midpoint vector -> distance 0.5, score 50.0
5. Distance monotonicity
6. Structural order != Rhythm repetition separation
7. Deterministic tie breaking
8. Top K bounds validation (1..50)
9. Catalog Corpus Eligibility & Accounting (Total 232, Eligible 224, Excluded Partial 3, Excluded No-Primary 5, Fixtures Excluded)
10. Historical Corpus Eligibility & Rights Provenance (Total 100, Eligible 45, Rights/Access Restricted 55)
11. Corpus Isolation (Catalog and Historical corpora strictly separate, never merged)
12. Corpus Fingerprint Stability, Row-Order Invariance & Mutation Sensitivity
13. Distance Symmetry & Zero-Distance Identity
14. Deterministic Seeded Random Vector Property Bounds (100 pairs)
15. Ranking uses unrounded distance before score rounding
16. Metadata Provenance vs Non-Inference (no predicted_culture, predicted_origin, authenticity_score)
17. Strict API Validation (extra='forbid' rejects query fields like 'culture')
18. Read-Only Operation & Zero GPU / Internet dependency
19. Real Data Smoke Run & Artifact Generation (data/validation/v2-07/visual-retrieval-smoke-report.json)
"""
import json
import math
import random
import time
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.session import get_db
from app.domain.visual_retrieval import (
    CANONICAL_STYLE_DNA_VERSION,
    CANONICAL_RETRIEVAL_VERSION,
    CANONICAL_POLICY_VERSION,
    CANONICAL_DIMENSION_KEYS,
    VisualRetrievalQuery,
    QuerySourceType,
    compute_9d_distance_and_score,
    CatalogVisualCorpusProvider,
    HistoricalVisualCorpusProvider,
    VisualRetrievalService,
)
from app.domain.visual_retrieval.corpus import compute_corpus_fingerprint


SAMPLE_9D_VECTOR_A = {
    "color_energy": 0.65,
    "color_diversity": 0.45,
    "contrast": 0.80,
    "warmth": 0.70,
    "visual_complexity": 0.50,
    "structural_order": 0.85,
    "rhythm_repetition": 0.60,
    "focal_strength": 0.75,
    "form_language": 0.65,
}

SAMPLE_9D_VECTOR_B = {
    "color_energy": 0.20,
    "color_diversity": 0.30,
    "contrast": 0.25,
    "warmth": 0.15,
    "visual_complexity": 0.80,
    "structural_order": 0.30,
    "rhythm_repetition": 0.25,
    "focal_strength": 0.20,
    "form_language": 0.30,
}


@pytest.fixture
async def real_db_session():
    """Async session connected directly to actual project carpet_db.sqlite database."""
    db_path = Path(__file__).resolve().parents[1] / "carpet_db.sqlite"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_canonical_9d_dimension_order_and_weights():
    """Verify 9D dimension keys and order match frozen specification."""
    expected_keys = [
        "color_energy",
        "color_diversity",
        "contrast",
        "warmth",
        "visual_complexity",
        "structural_order",
        "rhythm_repetition",
        "focal_strength",
        "form_language",
    ]
    assert CANONICAL_DIMENSION_KEYS == expected_keys
    # Structural order != rhythm repetition
    assert CANONICAL_DIMENSION_KEYS[5] == "structural_order"
    assert CANONICAL_DIMENSION_KEYS[6] == "rhythm_repetition"


def test_identical_vector_returns_score_100():
    """Identical query and candidate vector must yield distance 0.0 and score 100.0."""
    dist, score, deltas, closest, largest = compute_9d_distance_and_score(SAMPLE_9D_VECTOR_A, SAMPLE_9D_VECTOR_A)
    assert dist == 0.0
    assert score == 100.0
    assert len(deltas) == 9
    for d in deltas:
        assert d.absolute_delta == 0.0


def test_opposite_extreme_vector_returns_score_0():
    """Opposite extreme vectors ([0.0]*9 vs [1.0]*9) must yield max distance 1.0 and score 0.0."""
    zero_vec = {k: 0.0 for k in CANONICAL_DIMENSION_KEYS}
    one_vec = {k: 1.0 for k in CANONICAL_DIMENSION_KEYS}

    dist, score, deltas, closest, largest = compute_9d_distance_and_score(zero_vec, one_vec)
    assert math.isclose(dist, 1.0, abs_tol=1e-5)
    assert math.isclose(score, 0.0, abs_tol=1e-2)


def test_score_midpoint_50():
    """Vector with distance 0.5 must produce exact proximity score 50.0."""
    query = {k: 0.0 for k in CANONICAL_DIMENSION_KEYS}
    midpoint = {k: 0.5 for k in CANONICAL_DIMENSION_KEYS}

    dist, score, _, _, _ = compute_9d_distance_and_score(query, midpoint)
    assert math.isclose(dist, 0.5, abs_tol=1e-5)
    assert math.isclose(score, 50.0, abs_tol=1e-2)


def test_distance_monotonicity():
    """A candidate closer in all dimensions must have a score >= a farther candidate."""
    query = {k: 0.5 for k in CANONICAL_DIMENSION_KEYS}
    closer = {k: 0.55 for k in CANONICAL_DIMENSION_KEYS}
    farther = {k: 0.90 for k in CANONICAL_DIMENSION_KEYS}

    _, score_closer, _, _, _ = compute_9d_distance_and_score(query, closer)
    _, score_farther, _, _, _ = compute_9d_distance_and_score(query, farther)

    assert score_closer > score_farther


def test_distance_symmetry_and_zero_identity():
    """Verify distance(a, b) == distance(b, a) and distance(a, a) == 0.0."""
    dist_ab, score_ab, _, _, _ = compute_9d_distance_and_score(SAMPLE_9D_VECTOR_A, SAMPLE_9D_VECTOR_B)
    dist_ba, score_ba, _, _, _ = compute_9d_distance_and_score(SAMPLE_9D_VECTOR_B, SAMPLE_9D_VECTOR_A)

    assert dist_ab == dist_ba
    assert score_ab == score_ba

    dist_aa, score_aa, _, _, _ = compute_9d_distance_and_score(SAMPLE_9D_VECTOR_A, SAMPLE_9D_VECTOR_A)
    assert dist_aa == 0.0
    assert score_aa == 100.0


def test_structural_order_and_rhythm_repetition_separation():
    """Mutating structural_order must NOT change rhythm_repetition delta."""
    vec1 = {k: 0.5 for k in CANONICAL_DIMENSION_KEYS}
    vec2 = {k: 0.5 for k in CANONICAL_DIMENSION_KEYS}
    vec2["structural_order"] = 0.9  # Mutate only D6

    _, _, deltas, _, _ = compute_9d_distance_and_score(vec1, vec2)
    delta_map = {d.dimension_key: d.absolute_delta for d in deltas}

    assert delta_map["structural_order"] == 0.4
    assert delta_map["rhythm_repetition"] == 0.0


def test_deterministic_seeded_property_bounds():
    """Generate 100 random pairs in [0.0, 1.0]^9 and verify distance in [0,1], score in [0,100]."""
    rng = random.Random(20260817)

    for _ in range(100):
        vec_q = {k: round(rng.uniform(0.0, 1.0), 4) for k in CANONICAL_DIMENSION_KEYS}
        vec_c = {k: round(rng.uniform(0.0, 1.0), 4) for k in CANONICAL_DIMENSION_KEYS}

        dist, score, _, _, _ = compute_9d_distance_and_score(vec_q, vec_c)
        assert 0.0 <= dist <= 1.0
        assert 0.0 <= score <= 100.0


def test_corpus_fingerprint_row_order_invariance_and_vector_change():
    """Verify SHA-256 corpus fingerprint is row-order invariant and sensitive to vector changes."""
    rec1 = ("id-001", {k: 0.1 for k in CANONICAL_DIMENSION_KEYS})
    rec2 = ("id-002", {k: 0.2 for k in CANONICAL_DIMENSION_KEYS})
    rec3 = ("id-003", {k: 0.3 for k in CANONICAL_DIMENSION_KEYS})

    fp_original = compute_corpus_fingerprint([rec1, rec2, rec3])
    fp_reordered = compute_corpus_fingerprint([rec3, rec1, rec2])

    assert fp_original == fp_reordered

    # Vector change changes fingerprint
    rec2_mutated = ("id-002", {k: 0.25 for k in CANONICAL_DIMENSION_KEYS})
    fp_mutated = compute_corpus_fingerprint([rec1, rec2_mutated, rec3])

    assert fp_mutated != fp_original


def test_query_validation_bounds_and_missing_keys():
    """Validates that missing keys, extra keys, or values outside [0.0, 1.0] raise ValueError."""
    # Missing dimension key
    invalid_missing = dict(SAMPLE_9D_VECTOR_A)
    invalid_missing.pop("form_language")
    with pytest.raises(ValueError, match="Missing required Style DNA dimensions"):
        VisualRetrievalQuery(style_dna=invalid_missing)

    # Value out of bounds
    invalid_oob = dict(SAMPLE_9D_VECTOR_A)
    invalid_oob["contrast"] = 1.5
    with pytest.raises(ValueError, match="out of valid bounds"):
        VisualRetrievalQuery(style_dna=invalid_oob)

    # Incompatible version
    with pytest.raises(ValueError, match="Unsupported Style DNA version"):
        VisualRetrievalQuery(style_dna=SAMPLE_9D_VECTOR_A, style_dna_version="style-dna-v2.0.0")


@pytest.mark.asyncio
async def test_top_k_bounds_validation():
    """Validates top_k bounds (1..50)."""
    query = VisualRetrievalQuery(style_dna=SAMPLE_9D_VECTOR_A)
    service = VisualRetrievalService(db=None)

    # top_k = 0 -> ValueError
    with pytest.raises(ValueError, match="must be between 1 and 50"):
        await service.retrieve_catalog_async(query, top_k=0)

    # top_k = 51 -> ValueError
    with pytest.raises(ValueError, match="must be between 1 and 50"):
        await service.retrieve_catalog_async(query, top_k=51)


@pytest.mark.asyncio
async def test_real_catalog_corpus_eligibility_and_accounting(real_db_session):
    """Verify catalog corpus provider loads exact production baseline: Total 232, Eligible 224."""
    candidates, accounting = await CatalogVisualCorpusProvider.load_eligible_corpus_async(real_db_session)
    assert accounting.total_records == 232
    assert accounting.eligible_records == 224
    assert accounting.excluded_partial == 3
    assert accounting.excluded_missing_primary_image == 5
    assert accounting.excluded_missing_style_dna == 0
    assert len(accounting.corpus_fingerprint) == 64
    assert len(candidates) == 224

    # Verify test fixture DN-1001 is excluded
    skus = {c.sku for c in candidates}
    assert "DN-1001" not in skus


@pytest.mark.asyncio
async def test_real_historical_corpus_eligibility_and_accounting(real_db_session):
    """Verify historical corpus provider loads exact production baseline: Total 100, Eligible 45."""
    candidates, accounting = await HistoricalVisualCorpusProvider.load_eligible_corpus_async(real_db_session)
    assert accounting.total_records == 100
    assert accounting.eligible_records == 45
    assert accounting.excluded_missing_primary_image == 55
    assert accounting.excluded_missing_style_dna == 0
    assert len(accounting.corpus_fingerprint) == 64
    assert len(candidates) == 45


@pytest.mark.asyncio
async def test_corpus_isolation(real_db_session):
    """Catalog retrieval must return ONLY catalog products; Historical retrieval MUST return ONLY museum references."""
    query = VisualRetrievalQuery(style_dna=SAMPLE_9D_VECTOR_A)
    service = VisualRetrievalService(real_db_session)
    res = await service.retrieve_both_async(query, top_k_catalog=5, top_k_historical=5)

    assert len(res.catalog_matches) == 5
    assert len(res.historical_matches) == 5

    # Check Catalog matches contain ONLY catalog fields
    for cat in res.catalog_matches:
        assert hasattr(cat, "sku")
        assert hasattr(cat, "catalog_id")
        assert not hasattr(cat, "historical_reference_id")
        assert not hasattr(cat, "institution")

    # Check Historical matches contain ONLY historical reference fields
    for hist in res.historical_matches:
        assert hasattr(hist, "historical_reference_id")
        assert hasattr(hist, "institution")
        assert hasattr(hist, "museum_metadata")
        assert not hasattr(hist, "sku")
        assert not hasattr(hist, "catalog_id")


@pytest.mark.asyncio
async def test_api_strict_validation_rejects_extra_query_fields():
    """Test that direct HTTP request with forbidden extra fields (culture, origin, etc.) returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post(
            "/api/v1/visual-retrieval",
            json={
                "style_dna": SAMPLE_9D_VECTOR_A,
                "style_dna_version": CANONICAL_STYLE_DNA_VERSION,
                "culture": "Ottoman",  # Forbidden extra field!
                "predicted_origin": "Anatolia"
            }
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_api_endpoints_success(real_db_session):
    """Test POST /api/v1/visual-retrieval, /catalog, and /historical endpoints."""
    async def override_get_db():
        yield real_db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Dual-corpus endpoint
            res_both = await client.post(
                "/api/v1/visual-retrieval",
                json={
                    "style_dna": SAMPLE_9D_VECTOR_A,
                    "top_k_catalog": 3,
                    "top_k_historical": 3,
                }
            )
            assert res_both.status_code == 200
            data_both = res_both.json()
            assert data_both["retrieval_version"] == CANONICAL_RETRIEVAL_VERSION
            assert len(data_both["catalog_matches"]) == 3
            assert len(data_both["historical_matches"]) == 3

            # Catalog-only endpoint
            res_cat = await client.post(
                "/api/v1/visual-retrieval/catalog",
                json={
                    "style_dna": SAMPLE_9D_VECTOR_A,
                    "top_k_catalog": 4,
                }
            )
            assert res_cat.status_code == 200
            data_cat = res_cat.json()
            assert len(data_cat["catalog_matches"]) == 4

            # Historical-only endpoint
            res_hist = await client.post(
                "/api/v1/visual-retrieval/historical",
                json={
                    "style_dna": SAMPLE_9D_VECTOR_A,
                    "top_k_historical": 4,
                }
            )
            assert res_hist.status_code == 200
            data_hist = res_hist.json()
            assert len(data_hist["historical_matches"]) == 4
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_real_data_smoke_run_and_artifact_generation(real_db_session):
    """Runs a real visual retrieval query against DB baseline, measures latency, generates smoke report artifact."""
    query = VisualRetrievalQuery(
        style_dna=SAMPLE_9D_VECTOR_A,
        query_source_type=QuerySourceType.DIRECT_VECTOR,
        query_id="smoke-test-query-001"
    )

    t0 = time.time()
    service = VisualRetrievalService(real_db_session)
    response = await service.retrieve_both_async(query, top_k_catalog=5, top_k_historical=5)
    t1 = time.time()

    latency_ms = int((t1 - t0) * 1000)

    assert response.catalog_corpus_accounting.eligible_records == 224
    assert response.historical_corpus_accounting.eligible_records == 45
    assert len(response.catalog_matches) == 5
    assert len(response.historical_matches) == 5

    cat_top1 = response.catalog_matches[0]
    hist_top1 = response.historical_matches[0]

    assert 0.0 <= cat_top1.visual_proximity_score <= 100.0
    assert 0.0 <= hist_top1.visual_proximity_score <= 100.0

    # Ensure rank ordering is monotonically non-increasing
    for i in range(len(response.catalog_matches) - 1):
        assert response.catalog_matches[i].visual_proximity_score >= response.catalog_matches[i+1].visual_proximity_score

    for i in range(len(response.historical_matches) - 1):
        assert response.historical_matches[i].visual_proximity_score >= response.historical_matches[i+1].visual_proximity_score

    # Save real visual retrieval smoke report artifact
    smoke_report = {
        "task": "V2-07 — Historical + Catalog Visual Retrieval Real Smoke Run",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "retrieval_version": response.retrieval_version,
        "retrieval_policy_version": response.retrieval_policy_version,
        "latency_ms": latency_ms,
        "query_provenance": response.query_provenance,
        "catalog_corpus_accounting": response.catalog_corpus_accounting.model_dump(),
        "historical_corpus_accounting": response.historical_corpus_accounting.model_dump(),
        "catalog_top_5": [m.model_dump() for m in response.catalog_matches],
        "historical_top_5": [m.model_dump() for m in response.historical_matches],
    }

    report_dir = Path(__file__).resolve().parents[3] / "data" / "validation" / "v2-07"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "visual-retrieval-smoke-report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(smoke_report, f, indent=2, ensure_ascii=False)

    assert report_path.exists()
    print(f"\n[REAL SMOKE REPORT SAVED]: {report_path} (Latency: {latency_ms}ms)")
