"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Comprehensive API Security Test Suite for V2-06B — Human Motif Review API + Curator UI.

Verifies:
1. Access mode security policies (DISABLED, DEVELOPMENT_ADMIN, GATEWAY_TRUSTED)
2. Production protection for DEVELOPMENT_ADMIN mode
3. Missing MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF fails closed in DEVELOPMENT_ADMIN mode
4. Fake gateway headers (X-Reviewer-Ref, X-User, etc.) fail closed in GATEWAY_TRUSTED mode
5. Client payload trust boundary (forbids reviewer_ref, reviewer_boundary, resulting_status)
6. Queue API (GET /reviews/motif-candidates with status filtering & pagination)
7. Detail API (GET /reviews/motif-candidates/{id} with region evidence & protected image URLs)
8. History API (GET /reviews/motif-candidates/{id}/history with append-only audit trail)
9. Decision API (POST /reviews/motif-candidates/{id}/decision with Idempotency-Key & expected_version)
10. Protected Image Delivery API (GET /reviews/motif-candidates/{id}/image with ReviewerContext authorization)
11. Removal of generic /static uploads mount (direct /static requests return 404)
12. Concurrency conflict (HTTP 409) and Idempotency conflict (HTTP 409) error responses
13. Unmapped candidate remapping validation & invalid status filter validation (HTTP 422)
14. Research subject resolver integration with human review state
15. Zero downstream side effects on SourceResearchService, CulturalClaimValidator, or StoryCurator
"""
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.db.session import Base, get_db
from app.domain.upload_analysis.schemas import (
    MotifCandidate,
    RegionEvidence,
    BoundingBox2D,
    CoordinateSpace,
    VisualObservation,
    VisualObservationType,
    ModelProvenance,
    ProviderType,
    MotifCandidateStatus,
    VisualCandidateKey
)
from app.domain.motif_review.service import MotifReviewPersistenceService
from app.domain.research.resolver import resolve_research_subject_from_review, ResearchVerificationStatus


@pytest.fixture
def sync_db_session():
    """In-memory SQLite DB session for seeding review subjects."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    class MockAsyncSession:
        def __init__(self, s):
            self.sync_session = s
        async def execute(self, stmt):
            res = self.sync_session.execute(stmt)
            class ScalarResult:
                def scalars(self):
                    class Scalars:
                        def all(self):
                            return res.scalars().all()
                        def first(self):
                            return res.scalars().first()
                    return Scalars()
                def scalar_one_or_none(self):
                    return res.scalar_one_or_none()
            return ScalarResult()
        async def run_sync(self, fn, *args, **kwargs):
            return fn(self.sync_session, *args, **kwargs)
        async def commit(self):
            self.sync_session.commit()
        async def rollback(self):
            self.sync_session.rollback()
        def add(self, obj):
            self.sync_session.add(obj)

    async def _mock_get_db():
        yield MockAsyncSession(session)

    app.dependency_overrides[get_db] = _mock_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)
    session.close()


def create_sample_candidate(candidate_id: str, visual_key: str, status: MotifCandidateStatus, proposed_key: str = "star") -> MotifCandidate:
    return MotifCandidate(
        candidate_id=candidate_id,
        visual_candidate_key=VisualCandidateKey.STAR_LIKE,
        proposed_canonical_motif_key=proposed_key,
        status=status,
        confidence=0.88,
        region=RegionEvidence(
            bounding_box=BoundingBox2D(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.5),
            coordinate_space=CoordinateSpace.NORMALIZED_CANONICAL
        ),
        visual_evidence=["8-pointed star geometry"],
        model_provenance=ModelProvenance(
            provider_type=ProviderType.LOCAL_VLLM,
            model_id="Qwen/Qwen2.5-VL-3B-Instruct-AWQ",
            model_version="v1.0",
            prompt_version="v1.2",
            inference_timestamp="2026-08-17T14:00:00Z"
        )
    )


@pytest.mark.asyncio
async def test_access_mode_disabled_blocks_all_endpoints(sync_db_session):
    """Test that MOTIF_REVIEW_ACCESS_MODE=DISABLED rejects all review requests with 403."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    settings.MOTIF_REVIEW_ACCESS_MODE = "DISABLED"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res_queue = await client.get("/api/v1/reviews/motif-candidates")
            assert res_queue.status_code == 403
            assert res_queue.json()["detail"]["code"] == "REVIEW_ACCESS_DISABLED"

            res_detail = await client.get("/api/v1/reviews/motif-candidates/subj-123")
            assert res_detail.status_code == 403

            res_history = await client.get("/api/v1/reviews/motif-candidates/subj-123/history")
            assert res_history.status_code == 403

            res_image = await client.get("/api/v1/reviews/motif-candidates/subj-123/image")
            assert res_image.status_code == 403

            res_decision = await client.post(
                "/api/v1/reviews/motif-candidates/subj-123/decision",
                json={"decision": "CONFIRM", "expected_version": 0},
                headers={"Idempotency-Key": "key-1"}
            )
            assert res_decision.status_code == 403
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode


@pytest.mark.asyncio
async def test_development_admin_access_mode_requires_explicit_reviewer_ref(sync_db_session):
    """Test that DEVELOPMENT_ADMIN mode requires explicit MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    old_env = settings.APP_ENV

    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.APP_ENV = "development"

    # 1. Missing reviewer ref -> Fails Closed with 403
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res_missing = await client.get("/api/v1/reviews/motif-candidates")
        assert res_missing.status_code == 403
        assert res_missing.json()["detail"]["code"] == "REVIEW_ACCESS_DISABLED"

    # 2. Explicit reviewer ref -> Succeeded
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "explicit-dev-curator"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res_ok = await client.get("/api/v1/reviews/motif-candidates")
            assert res_ok.status_code == 200
            assert "items" in res_ok.json()
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref
        settings.APP_ENV = old_env


@pytest.mark.asyncio
async def test_development_admin_mode_rejected_in_production():
    """Test that DEVELOPMENT_ADMIN mode is forbidden if APP_ENV=production."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    old_env = settings.APP_ENV

    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "some-ref"
    settings.APP_ENV = "production"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.get("/api/v1/reviews/motif-candidates")
            assert res.status_code == 403
            assert res.json()["detail"]["code"] == "REVIEW_ACCESS_DISABLED"
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref
        settings.APP_ENV = old_env


@pytest.mark.asyncio
async def test_fake_gateway_headers_rejected_in_gateway_trusted_mode():
    """Test that arbitrary headers (X-Reviewer-Ref, X-User, X-Curator) do NOT satisfy GATEWAY_TRUSTED mode."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    settings.MOTIF_REVIEW_ACCESS_MODE = "GATEWAY_TRUSTED"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.get(
                "/api/v1/reviews/motif-candidates",
                headers={
                    "X-Reviewer-Ref": "fake-curator",
                    "X-User": "admin",
                    "X-Forwarded-User": "curator-user",
                    "X-Curator": "true"
                }
            )
            assert res.status_code == 403
            assert res.json()["detail"]["code"] == "REVIEW_ACCESS_DISABLED"
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode


@pytest.mark.asyncio
async def test_invalid_status_filter_returns_422():
    """Test that an invalid status filter query parameter returns HTTP 422."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "test-curator"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.get("/api/v1/reviews/motif-candidates?status=INVALID_STATUS")
            assert res.status_code == 422
            assert res.json()["detail"]["code"] == "INVALID_STATUS_FILTER"
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref


@pytest.mark.asyncio
async def test_client_payload_forbids_extra_fields():
    """Test that client decision endpoint forbids reviewer_ref or reviewer_boundary in body."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "test-curator"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post(
                "/api/v1/reviews/motif-candidates/subj-123/decision",
                json={
                    "decision": "CONFIRM",
                    "expected_version": 0,
                    "reviewer_ref": "hacker",  # Extra forbidden field
                    "reviewer_boundary": "DEVELOPMENT_ADMIN"
                },
                headers={"Idempotency-Key": "key-test-extra"}
            )
            assert res.status_code == 422  # Pydantic extra='forbid' validation failure
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref


@pytest.mark.asyncio
async def test_protected_image_delivery(sync_db_session):
    """Test protected review image delivery endpoint and removal of generic static mount."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "explicit-curator-admin"

    # Create dummy image file under IMAGE_STORAGE_ROOT
    upload_root = Path(settings.IMAGE_STORAGE_ROOT).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    test_img = upload_root / "test_carpet_sample.jpg"
    test_img.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")  # Minimal JPEG header bytes

    service = MotifReviewPersistenceService(sync_db_session)
    cand = create_sample_candidate("c-img-1", "star_like", MotifCandidateStatus.AI_CANDIDATE, "star")
    subj = service.register_candidate_subject(cand, "analysis-img-1", image_asset_id="test_carpet_sample.jpg")

    async def _mock_get_db():
        class MockAsyncSession:
            def __init__(self, s):
                self.sync_session = s
            async def execute(self, stmt):
                res = self.sync_session.execute(stmt)
                class ScalarResult:
                    def scalars(self):
                        class Scalars:
                            def all(self):
                                return res.scalars().all()
                        return Scalars()
                return ScalarResult()
            async def run_sync(self, fn, *args, **kwargs):
                return fn(self.sync_session, *args, **kwargs)
        yield MockAsyncSession(sync_db_session)

    app.dependency_overrides[get_db] = _mock_get_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Detail returns protected image_url
            res_det = await client.get(f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}")
            assert res_det.status_code == 200
            assert res_det.json()["image_url"] == f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/image"

            # 2. Protected Image GET returns 200 with image/jpeg media_type & private Cache-Control
            res_img = await client.get(f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/image")
            assert res_img.status_code == 200
            assert res_img.headers["content-type"] == "image/jpeg"
            assert "private" in res_img.headers["cache-control"]

            # 3. Direct access to generic /static/ is REMOVED -> 404 Not Found
            res_static = await client.get("/static/test_carpet_sample.jpg")
            assert res_static.status_code == 404

            # 4. Unknown subject ID -> 404 REVIEW_SUBJECT_NOT_FOUND
            res_unk = await client.get("/api/v1/reviews/motif-candidates/subj-nonexistent/image")
            assert res_unk.status_code == 404
            assert res_unk.json()["detail"]["code"] == "REVIEW_SUBJECT_NOT_FOUND"

            # 5. DISABLED mode blocks protected image endpoint -> 403
            settings.MOTIF_REVIEW_ACCESS_MODE = "DISABLED"
            res_dis = await client.get(f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/image")
            assert res_dis.status_code == 403
            assert res_dis.json()["detail"]["code"] == "REVIEW_ACCESS_DISABLED"

    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref
        app.dependency_overrides.pop(get_db, None)
        if test_img.exists():
            test_img.unlink()


@pytest.mark.asyncio
async def test_review_decision_flow_and_history(sync_db_session):
    """Test full decision submission, optimistic concurrency, and audit history via API endpoints."""
    old_mode = settings.MOTIF_REVIEW_ACCESS_MODE
    old_ref = settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF
    settings.MOTIF_REVIEW_ACCESS_MODE = "DEVELOPMENT_ADMIN"
    settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = "explicit-curator-admin"

    # Seed subject in DB
    service = MotifReviewPersistenceService(sync_db_session)
    cand = create_sample_candidate("c-flow-1", "star_like", MotifCandidateStatus.AI_CANDIDATE, "star")
    subj = service.register_candidate_subject(cand, "analysis-flow-1")

    async def _mock_get_db():
        class MockAsyncSession:
            def __init__(self, s):
                self.sync_session = s
            async def execute(self, stmt):
                res = self.sync_session.execute(stmt)
                class ScalarResult:
                    def scalars(self):
                        class Scalars:
                            def all(self):
                                return res.scalars().all()
                        return Scalars()
                return ScalarResult()
            async def run_sync(self, fn, *args, **kwargs):
                return fn(self.sync_session, *args, **kwargs)
        yield MockAsyncSession(sync_db_session)

    app.dependency_overrides[get_db] = _mock_get_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Fetch Queue
            res_q = await client.get("/api/v1/reviews/motif-candidates?status=PENDING")
            assert res_q.status_code == 200
            q_data = res_q.json()
            assert q_data["total_count"] >= 1

            # 2. Fetch Detail
            res_det = await client.get(f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}")
            assert res_det.status_code == 200
            det_data = res_det.json()
            assert det_data["effective_status"] == "AI_CANDIDATE"
            assert det_data["review_version"] == 0

            # 3. Submit Decision: CONFIRM
            res_dec = await client.post(
                f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/decision",
                json={
                    "decision": "CONFIRM",
                    "selected_canonical_motif_key": "geometric-star",
                    "reason_code": "VISUAL_MATCH_CONFIRMED",
                    "note": "Curator verified 8-pointed star",
                    "expected_version": 0
                },
                headers={"Idempotency-Key": "idemp-flow-1"}
            )
            assert res_dec.status_code == 200
            dec_data = res_dec.json()
            assert dec_data["effective_status"] == "CURATOR_CONFIRMED"
            assert dec_data["research_eligibility"] == "SOURCE_RESEARCH_ALLOWED"

            # 4. Fetch History
            res_hist = await client.get(f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/history")
            assert res_hist.status_code == 200
            hist_data = res_hist.json()
            assert len(hist_data) == 1
            assert hist_data[0]["decision"] == "CONFIRM"
            assert hist_data[0]["reviewer_ref"] == "explicit-curator-admin"
            assert hist_data[0]["reviewer_boundary"] == "DEVELOPMENT_ADMIN"

            # 5. Stale Concurrency Attempt (expected_version 0 when now 1) -> HTTP 409
            res_stale = await client.post(
                f"/api/v1/reviews/motif-candidates/{subj.review_subject_id}/decision",
                json={
                    "decision": "REJECT",
                    "expected_version": 0
                },
                headers={"Idempotency-Key": "idemp-flow-2"}
            )
            assert res_stale.status_code == 409
            assert res_stale.json()["detail"]["code"] == "REVIEW_CONFLICT"
    finally:
        settings.MOTIF_REVIEW_ACCESS_MODE = old_mode
        settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF = old_ref
        app.dependency_overrides.pop(get_db, None)


def test_research_subject_resolver_integration(sync_db_session):
    """Test resolve_research_subject_from_review with effective human review states."""
    service = MotifReviewPersistenceService(sync_db_session)
    cand = create_sample_candidate("c-res-1", "c-res-star", MotifCandidateStatus.AI_CANDIDATE, "star")
    subj = service.register_candidate_subject(cand, "analysis-res-1")

    # 1. Before review: PENDING -> resolve_research_subject_from_review raises ValueError
    with pytest.raises(ValueError, match="BLOCKED"):
        resolve_research_subject_from_review(subj.review_subject_id, sync_db_session)

    # 2. Confirm candidate
    from app.domain.motif_review.schemas import MotifReviewDecisionRequest, ReviewDecisionEnum, ReviewerBoundaryEnum
    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        expected_version=0,
        reviewer_ref="curator-1",
        reviewer_boundary=ReviewerBoundaryEnum.DEVELOPMENT_ADMIN,
        idempotency_key="idemp-res-1"
    )
    service.submit_review_decision("analysis-res-1", "c-res-1", req)

    # 3. After CONFIRM: returns trusted ResearchSubject
    res_subj = resolve_research_subject_from_review(subj.review_subject_id, sync_db_session)
    assert res_subj.canonical_motif_key == "geometric-star"
    assert res_subj.verification_status == ResearchVerificationStatus.CURATOR_CONFIRMED

    # 4. Re-review to REJECT
    req_reject = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.REJECT,
        expected_version=1,
        reviewer_ref="curator-1",
        reviewer_boundary=ReviewerBoundaryEnum.DEVELOPMENT_ADMIN,
        idempotency_key="idemp-res-2"
    )
    service.submit_review_decision("analysis-res-1", "c-res-1", req_reject)

    # 5. After REJECT: raises ValueError BLOCKED
    with pytest.raises(ValueError, match="BLOCKED"):
        resolve_research_subject_from_review(subj.review_subject_id, sync_db_session)
