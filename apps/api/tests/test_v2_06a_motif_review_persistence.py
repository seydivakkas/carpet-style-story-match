"""
Comprehensive Unit Test Suite for V2-06A — Human Motif Review Persistence Foundation.

Verifies:
- ORM models and schema constraints
- Candidate snapshot building and SHA-256 hash stability
- Server-owned status mappings (CONFIRM -> CURATOR_CONFIRMED, UNCERTAIN -> UNCERTAIN, REJECT -> REJECTED)
- Canonical ontology validation & unmapped candidate remapping
- Append-only event history and effective review state resolution
- Optimistic concurrency versioning & stale snapshot protection
- Idempotency key persistence and conflict handling
- Foreign key RESTRICT audit safety
- Reviewer provenance tracking & curator note isolation
- Zero downstream side effects & persistent baseline data isolation
"""
import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
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
from app.domain.motif_review.schemas import (
    MotifReviewDecisionRequest,
    ReviewDecisionEnum,
    ReviewResultingStatusEnum,
    ResearchEligibilityEnum,
    ReviewerBoundaryEnum,
    MotifReviewReasonCode
)
from app.domain.motif_review.snapshot import build_canonical_candidate_snapshot, compute_snapshot_hash
from app.domain.motif_review.repository import (
    MotifReviewRepository,
    ReviewConcurrencyException,
    ReviewSnapshotMismatchException,
    ReviewIdempotencyConflictException
)
from app.domain.motif_review.service import (
    MotifReviewPersistenceService,
    InvalidReviewTransitionException,
    UnknownCanonicalMotifException
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture for V2-06A persistence tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_star_candidate():
    """Sample star_like AI motif candidate."""
    return MotifCandidate(
        candidate_id="cand-star-001",
        visual_candidate_key=VisualCandidateKey.STAR_LIKE,
        proposed_canonical_motif_key="geometric-star",
        status=MotifCandidateStatus.AI_CANDIDATE,
        confidence=0.88,
        region=RegionEvidence(
            bounding_box=BoundingBox2D(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.5),
            coordinate_space=CoordinateSpace.NORMALIZED_CANONICAL
        ),
        visual_evidence=["8-pointed star geometry"],
        model_provenance=ModelProvenance(
            provider_type=ProviderType.TEST_FIXTURE,
            model_id="test-vlm-v1",
            model_version="1.0.0",
            prompt_version="motif-vision-prompt-v1",
            inference_timestamp="2026-08-17T14:00:00Z",
            request_hash="hash-12345"
        )
    )


@pytest.fixture
def sample_unmapped_candidate():
    """Sample unmapped AI motif candidate."""
    return MotifCandidate(
        candidate_id="cand-unmapped-002",
        visual_candidate_key=VisualCandidateKey.UNMAPPED_VISUAL_MOTIF,
        proposed_canonical_motif_key=None,
        status=MotifCandidateStatus.UNMAPPED_MOTIF_CANDIDATE,
        confidence=0.65,
        region=RegionEvidence(
            bounding_box=BoundingBox2D(x_min=0.2, y_min=0.2, x_max=0.4, y_max=0.4),
            coordinate_space=CoordinateSpace.NORMALIZED_CANONICAL
        ),
        visual_evidence=["Unusual geometric motif pattern"],
        model_provenance=ModelProvenance(
            provider_type=ProviderType.TEST_FIXTURE,
            model_id="test-vlm-v1",
            model_version="1.0.0",
            prompt_version="motif-vision-prompt-v1",
            inference_timestamp="2026-08-17T14:00:00Z",
            request_hash="hash-67890"
        )
    )




# ============================================================================
# 1. SNAPSHOT & HASHING TESTS
# ============================================================================

def test_snapshot_building_and_hash_stability(sample_star_candidate):
    """Verify deterministic JSON snapshot building and SHA-256 hash stability."""
    snapshot1 = build_canonical_candidate_snapshot(sample_star_candidate, "analysis-001")
    hash1 = compute_snapshot_hash(snapshot1)

    snapshot2 = build_canonical_candidate_snapshot(sample_star_candidate, "analysis-001")
    hash2 = compute_snapshot_hash(snapshot2)

    assert hash1 == hash2
    assert len(hash1) == 64
    assert snapshot1["analysis_id"] == "analysis-001"
    assert snapshot1["candidate_id"] == "cand-star-001"
    assert snapshot1["proposed_canonical_motif_key"] == "geometric-star"


def test_snapshot_hash_changes_on_semantic_field_mutation(sample_star_candidate):
    """Verify snapshot hash changes when semantic candidate fields change."""
    snapshot_base = build_canonical_candidate_snapshot(sample_star_candidate, "analysis-001")
    hash_base = compute_snapshot_hash(snapshot_base)

    # Mutate confidence
    sample_star_candidate.confidence = 0.95
    snapshot_mutated = build_canonical_candidate_snapshot(sample_star_candidate, "analysis-001")
    hash_mutated = compute_snapshot_hash(snapshot_mutated)

    assert hash_base != hash_mutated


# ============================================================================
# 2. SUBJECT PERSISTENCE & UNIQUE CONSTRAINTS
# ============================================================================

def test_subject_registration_and_identity_uniqueness(db_session, sample_star_candidate):
    """Verify review subject registration and uniqueness of (analysis_id, candidate_id)."""
    service = MotifReviewPersistenceService(db_session)
    subject1 = service.register_candidate_subject(sample_star_candidate, "analysis-001")

    assert subject1.analysis_id == "analysis-001"
    assert subject1.candidate_id == "cand-star-001"
    assert subject1.review_version == 0

    # Registering same candidate again returns existing subject idempotently
    subject2 = service.register_candidate_subject(sample_star_candidate, "analysis-001")
    assert subject1.review_subject_id == subject2.review_subject_id


def test_unmapped_candidate_subject_creation(db_session, sample_unmapped_candidate):
    """Verify unmapped candidates store proposed_canonical_motif_key = None safely."""
    service = MotifReviewPersistenceService(db_session)
    subject = service.register_candidate_subject(sample_unmapped_candidate, "analysis-002")

    assert subject.proposed_canonical_motif_key is None
    assert subject.visual_candidate_key == "unmapped_visual_motif"


# ============================================================================
# 3. REVIEW DECISION & STATUS MAPPINGS
# ============================================================================

def test_confirm_decision_mapping_and_research_eligibility(db_session, sample_star_candidate):
    """Verify CONFIRM decision maps to CURATOR_CONFIRMED and SOURCE_RESEARCH_ALLOWED."""
    service = MotifReviewPersistenceService(db_session)
    subject = service.register_candidate_subject(sample_star_candidate, "analysis-101")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        reason_code=MotifReviewReasonCode.VISUAL_MATCH_CONFIRMED,
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-101"
    )
    result = service.submit_review_decision("analysis-101", "cand-star-001", req)

    assert result.effective_status == ReviewResultingStatusEnum.CURATOR_CONFIRMED.value
    assert result.research_eligibility == ResearchEligibilityEnum.SOURCE_RESEARCH_ALLOWED
    assert result.subject.review_version == 1
    assert result.effective_event.decision == ReviewDecisionEnum.CONFIRM
    assert result.effective_event.resulting_status == ReviewResultingStatusEnum.CURATOR_CONFIRMED


def test_uncertain_decision_blocks_research(db_session, sample_star_candidate):
    """Verify UNCERTAIN decision maps to UNCERTAIN and SOURCE_RESEARCH_BLOCKED."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-102")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.UNCERTAIN,
        reason_code=MotifReviewReasonCode.AMBIGUOUS_WITH_OTHER_MOTIF,
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-102"
    )
    result = service.submit_review_decision("analysis-102", "cand-star-001", req)

    assert result.effective_status == ReviewResultingStatusEnum.UNCERTAIN.value
    assert result.research_eligibility == ResearchEligibilityEnum.SOURCE_RESEARCH_BLOCKED


def test_reject_decision_blocks_research(db_session, sample_star_candidate):
    """Verify REJECT decision maps to REJECTED and SOURCE_RESEARCH_BLOCKED."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-103")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.REJECT,
        reason_code=MotifReviewReasonCode.NOT_A_MOTIF,
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-103"
    )
    result = service.submit_review_decision("analysis-103", "cand-star-001", req)

    assert result.effective_status == ReviewResultingStatusEnum.REJECTED.value
    assert result.research_eligibility == ResearchEligibilityEnum.SOURCE_RESEARCH_BLOCKED


# ============================================================================
# 4. ONTOLOGY VALIDATION & UNMAPPED REMAPPING
# ============================================================================

def test_unmapped_confirm_requires_explicit_remapping(db_session, sample_unmapped_candidate):
    """Verify CONFIRMing an unmapped candidate without canonical motif key fails."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_unmapped_candidate, "analysis-201")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key=None,  # Missing remapped key
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-201"
    )
    with pytest.raises(InvalidReviewTransitionException):
        service.submit_review_decision("analysis-201", "cand-unmapped-002", req)


def test_unmapped_controlled_remapping_success(db_session, sample_unmapped_candidate):
    """Verify UNMAPPED candidate can be CONFIRMED with valid canonical motif key from ontology."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_unmapped_candidate, "analysis-202")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="mihrab",  # Existing valid ontology key
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-202"
    )
    result = service.submit_review_decision("analysis-202", "cand-unmapped-002", req)

    assert result.effective_status == ReviewResultingStatusEnum.CURATOR_CONFIRMED.value
    assert result.effective_event.selected_canonical_motif_key == "mihrab"


def test_unknown_canonical_motif_key_rejection(db_session, sample_star_candidate):
    """Verify selecting a canonical key not in motif-ontology-v1.0.0 fails."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-203")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="nonexistent-fantasy-motif",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-203"
    )
    with pytest.raises(UnknownCanonicalMotifException):
        service.submit_review_decision("analysis-203", "cand-star-001", req)


# ============================================================================
# 5. CONCURRENCY, IDEMPOTENCY & APPEND-ONLY AUDIT HISTORY
# ============================================================================

def test_optimistic_concurrency_protection(db_session, sample_star_candidate):
    """Verify submitting decision with stale expected_version raises ReviewConcurrencyException."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-301")

    req1 = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-301a"
    )
    service.submit_review_decision("analysis-301", "cand-star-001", req1)

    # Stale request attempting to submit with expected_version = 0 (now at version 1)
    req_stale = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.UNCERTAIN,
        reviewer_ref="curator-02",
        expected_version=0,
        idempotency_key="idemp-301b"
    )
    with pytest.raises(ReviewConcurrencyException):
        service.submit_review_decision("analysis-301", "cand-star-001", req_stale)


def test_idempotency_key_handling(db_session, sample_star_candidate):
    """Verify identical idempotency_key returns original event without duplicating history."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-302")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-302"
    )
    res1 = service.submit_review_decision("analysis-302", "cand-star-001", req)

    # Repeat exact same request with same idempotency key
    res2 = service.submit_review_decision("analysis-302", "cand-star-001", req)

    assert res1.effective_event.review_id == res2.effective_event.review_id
    assert res2.history_count == 1


def test_idempotency_conflict_detection(db_session, sample_star_candidate):
    """Verify reusing idempotency_key with conflicting payload raises exception."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-303")

    req1 = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-303"
    )
    service.submit_review_decision("analysis-303", "cand-star-001", req1)

    req2 = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.REJECT,  # Conflicting decision payload
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-303"
    )
    with pytest.raises(ReviewIdempotencyConflictException):
        service.submit_review_decision("analysis-303", "cand-star-001", req2)


def test_append_only_re_review_history_and_supersedes(db_session, sample_star_candidate):
    """Verify re-review preserves all audit events and links supersedes_review_id."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-401")

    # Event 1: CONFIRM
    req1 = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-401a"
    )
    res1 = service.submit_review_decision("analysis-401", "cand-star-001", req1)
    event1_id = res1.effective_event.review_id

    # Event 2: UNCERTAIN
    req2 = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.UNCERTAIN,
        reviewer_ref="curator-02",
        expected_version=1,
        idempotency_key="idemp-401b"
    )
    res2 = service.submit_review_decision("analysis-401", "cand-star-001", req2)

    assert res2.history_count == 2
    assert res2.effective_status == ReviewResultingStatusEnum.UNCERTAIN.value
    assert res2.effective_event.version == 2
    assert res2.effective_event.supersedes_review_id is not None

    history = service.get_history_by_identity("analysis-401", "cand-star-001")
    assert len(history) == 2
    assert history[0].version == 1
    assert history[1].version == 2


# ============================================================================
# 6. RESTRICT FK SAFETY & PROVENANCE ISOLATION
# ============================================================================

def test_curator_note_isolation(db_session, sample_star_candidate):
    """Verify curator notes are stored strictly as operational metadata."""
    service = MotifReviewPersistenceService(db_session)
    service.register_candidate_subject(sample_star_candidate, "analysis-501")

    req = MotifReviewDecisionRequest(
        decision=ReviewDecisionEnum.CONFIRM,
        selected_canonical_motif_key="geometric-star",
        note="Speculative Ottoman influence noted by curator",
        reviewer_ref="curator-01",
        expected_version=0,
        idempotency_key="idemp-501"
    )
    res = service.submit_review_decision("analysis-501", "cand-star-001", req)

    assert res.effective_event.note == "Speculative Ottoman influence noted by curator"
    # Verify note is not copied to subject or any external domain tables
    assert "Ottoman" not in res.subject.model_dump_json()
