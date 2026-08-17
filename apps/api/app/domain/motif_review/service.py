"""
Domain service for Human Motif Review Persistence v1.

Manages subject registration from AI candidates, decision mapping, ontology validation,
concurrency versioning, idempotency checks, and effective research eligibility calculation.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.domain.upload_analysis.schemas import MotifCandidate
from app.domain.upload_analysis.motif_ontology import CANONICAL_PRODUCTION_MOTIFS
from app.domain.motif_review.schemas import (
    MotifReviewSubject,
    MotifReviewDecisionRequest,
    MotifReviewEvent,
    MotifReviewResult,
    ReviewDecisionEnum,
    ReviewResultingStatusEnum,
    ResearchEligibilityEnum,
    ReviewerBoundaryEnum,
    MotifReviewReasonCode,
    MOTIF_REVIEW_SCHEMA_VERSION
)
from app.domain.motif_review.snapshot import build_canonical_candidate_snapshot, compute_snapshot_hash
from app.domain.motif_review.repository import (
    MotifReviewRepository,
    MotifReviewSubjectModel,
    MotifReviewEventModel,
    ReviewConcurrencyException,
    ReviewSnapshotMismatchException,
    ReviewIdempotencyConflictException
)


class InvalidReviewTransitionException(Exception):
    """Raised when review request violates status transition rules (e.g. unmapped confirm without canonical key)."""
    pass


class UnknownCanonicalMotifException(Exception):
    """Raised when selected_canonical_motif_key does not exist in frozen ontology."""
    pass


class MotifReviewPersistenceService:
    """Service encapsulating domain logic for durable motif review persistence."""

    def __init__(self, db: Session):
        self.db = db

    def register_candidate_subject(
        self,
        candidate: MotifCandidate,
        analysis_id: str,
        image_asset_id: Optional[str] = None,
        ontology_version: str = "motif-ontology-v1.0.0"
    ) -> MotifReviewSubject:
        """
        Build canonical candidate snapshot, compute hash, and register review subject if absent.
        """
        snapshot = build_canonical_candidate_snapshot(candidate, analysis_id, ontology_version)
        snapshot_hash = compute_snapshot_hash(snapshot)

        proposed_key = (
            candidate.proposed_canonical_motif_key.value
            if hasattr(candidate.proposed_canonical_motif_key, "value")
            else candidate.proposed_canonical_motif_key
        ) if candidate.proposed_canonical_motif_key else None

        visual_key = (
            candidate.visual_candidate_key.value
            if hasattr(candidate.visual_candidate_key, "value")
            else str(candidate.visual_candidate_key)
        )

        model_provenance_dict = {
            "provider_type": candidate.model_provenance.provider_type.value if hasattr(candidate.model_provenance.provider_type, "value") else str(candidate.model_provenance.provider_type),
            "model_id": candidate.model_provenance.model_id,
            "prompt_version": candidate.model_provenance.prompt_version,
            "request_hash": candidate.model_provenance.request_hash
        }

        subject_model = MotifReviewRepository.create_subject(
            db=self.db,
            analysis_id=analysis_id,
            candidate_id=candidate.candidate_id,
            visual_candidate_key=visual_key,
            proposed_canonical_motif_key=proposed_key,
            original_candidate_status=candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status),

            candidate_confidence=candidate.confidence,
            candidate_snapshot=snapshot,
            snapshot_hash=snapshot_hash,
            model_provenance=model_provenance_dict,
            image_asset_id=image_asset_id,
            ontology_version=ontology_version
        )

        return self._to_subject_dto(subject_model)

    def submit_review_decision(
        self,
        analysis_id: str,
        candidate_id: str,
        request: MotifReviewDecisionRequest
    ) -> MotifReviewResult:
        """
        Submit a human curator decision for a candidate subject.
        
        Enforces:
        - Server-owned status mapping (CONFIRM -> CURATOR_CONFIRMED, UNCERTAIN -> UNCERTAIN, REJECT -> REJECTED)
        - Ontology resolution for selected_canonical_motif_key
        - Unmapped candidate remap requirement
        - Candidate snapshot hash matching
        - Optimistic concurrency version matching
        - Idempotency key handling
        """
        subject_model = MotifReviewRepository.get_subject_by_identity(self.db, analysis_id, candidate_id)
        if subject_model is None:
            raise KeyError(f"Review subject for analysis '{analysis_id}' and candidate '{candidate_id}' not found.")

        # 1. Determine canonical motif key and validate against ontology
        selected_key = request.selected_canonical_motif_key
        if request.decision == ReviewDecisionEnum.CONFIRM:
            if not selected_key:
                selected_key = subject_model.proposed_canonical_motif_key

            if not selected_key:
                raise InvalidReviewTransitionException(
                    "CONFIRM decision requires a valid canonical motif key (unmapped candidates require explicit remapping)."
                )

            if selected_key not in CANONICAL_PRODUCTION_MOTIFS:
                raise UnknownCanonicalMotifException(
                    f"Selected canonical motif key '{selected_key}' is not in frozen production ontology."
                )

        # 2. Server-owned resulting status mapping
        if request.decision == ReviewDecisionEnum.CONFIRM:
            resulting_status = ReviewResultingStatusEnum.CURATOR_CONFIRMED
        elif request.decision == ReviewDecisionEnum.UNCERTAIN:
            resulting_status = ReviewResultingStatusEnum.UNCERTAIN
        else:
            resulting_status = ReviewResultingStatusEnum.REJECTED

        # 3. Append review event atomically
        event_model = MotifReviewRepository.append_review_event(
            db=self.db,
            subject=subject_model,
            decision=request.decision.value,
            resulting_status=resulting_status.value,
            selected_canonical_motif_key=selected_key,
            reason_code=request.reason_code.value if request.reason_code else None,
            note=request.note,
            reviewer_ref=request.reviewer_ref,
            reviewer_boundary=request.reviewer_boundary.value,
            candidate_snapshot_hash=subject_model.snapshot_hash,
            idempotency_key=request.idempotency_key,
            expected_version=request.expected_version
        )

        return self.get_effective_result_by_identity(analysis_id, candidate_id)

    def get_effective_result_by_identity(
        self,
        analysis_id: str,
        candidate_id: str
    ) -> MotifReviewResult:
        """Calculate deterministic effective review state and research eligibility."""
        subject_model = MotifReviewRepository.get_subject_by_identity(self.db, analysis_id, candidate_id)
        if subject_model is None:
            raise KeyError(f"Review subject for analysis '{analysis_id}' and candidate '{candidate_id}' not found.")

        return self._build_effective_result(subject_model)

    def get_history_by_identity(
        self,
        analysis_id: str,
        candidate_id: str
    ) -> List[MotifReviewEvent]:
        """Retrieve complete append-only review event history for a subject."""
        subject_model = MotifReviewRepository.get_subject_by_identity(self.db, analysis_id, candidate_id)
        if subject_model is None:
            raise KeyError(f"Review subject for analysis '{analysis_id}' and candidate '{candidate_id}' not found.")

        events = MotifReviewRepository.get_history(self.db, subject_model.id)
        return [self._to_event_dto(e) for e in events]

    def _build_effective_result(self, subject_model: MotifReviewSubjectModel) -> MotifReviewResult:
        """Internal helper to construct MotifReviewResult DTO."""
        subject_dto = self._to_subject_dto(subject_model)
        effective_event_model = MotifReviewRepository.get_effective_event(self.db, subject_model.id)
        history = MotifReviewRepository.get_history(self.db, subject_model.id)

        if effective_event_model is None:
            effective_status = subject_model.original_candidate_status
            research_eligibility = ResearchEligibilityEnum.SOURCE_RESEARCH_BLOCKED
            effective_event_dto = None
        else:
            effective_event_dto = self._to_event_dto(effective_event_model)
            effective_status = effective_event_model.resulting_status
            if effective_event_model.resulting_status == ReviewResultingStatusEnum.CURATOR_CONFIRMED.value:
                research_eligibility = ResearchEligibilityEnum.SOURCE_RESEARCH_ALLOWED
            else:
                research_eligibility = ResearchEligibilityEnum.SOURCE_RESEARCH_BLOCKED

        return MotifReviewResult(
            review_version_schema=MOTIF_REVIEW_SCHEMA_VERSION,
            subject=subject_dto,
            effective_event=effective_event_dto,
            effective_status=effective_status,
            research_eligibility=research_eligibility,
            history_count=len(history)
        )

    @staticmethod
    def _to_subject_dto(model: MotifReviewSubjectModel) -> MotifReviewSubject:
        return MotifReviewSubject(
            review_subject_id=model.review_subject_id,
            analysis_id=model.analysis_id,
            candidate_id=model.candidate_id,
            image_asset_id=model.image_asset_id,
            visual_candidate_key=model.visual_candidate_key,
            proposed_canonical_motif_key=model.proposed_canonical_motif_key,
            original_candidate_status=model.original_candidate_status,
            candidate_confidence=model.candidate_confidence,
            candidate_snapshot=model.candidate_snapshot,
            snapshot_hash=model.snapshot_hash,
            model_provenance=model.model_provenance,
            ontology_version=model.ontology_version,
            review_version=model.review_version,
            created_at=model.created_at
        )

    @staticmethod
    def _to_event_dto(model: MotifReviewEventModel) -> MotifReviewEvent:
        return MotifReviewEvent(
            review_id=model.review_id,
            review_subject_id=str(model.review_subject_id),
            decision=ReviewDecisionEnum(model.decision),
            resulting_status=ReviewResultingStatusEnum(model.resulting_status),
            selected_canonical_motif_key=model.selected_canonical_motif_key,
            reason_code=MotifReviewReasonCode(model.reason_code) if model.reason_code else None,
            note=model.note,
            reviewer_ref=model.reviewer_ref,
            reviewer_boundary=ReviewerBoundaryEnum(model.reviewer_boundary),
            candidate_snapshot_hash=model.candidate_snapshot_hash,
            idempotency_key=model.idempotency_key,
            version=model.version,
            supersedes_review_id=str(model.supersedes_review_id) if model.supersedes_review_id else None,
            created_at=model.created_at
        )
