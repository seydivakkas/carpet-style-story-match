"""
Database repository operations for Human Motif Review Persistence v1.

Encapsulates atomic subject creation, append-only event recording, optimistic concurrency
version verification, idempotency handling, and effective review resolution.
"""
from typing import List, Optional, Tuple, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, update

from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel


class ReviewConcurrencyException(Exception):
    """Raised when expected review_version token does not match subject review_version."""
    pass


class ReviewSnapshotMismatchException(Exception):
    """Raised when request candidate snapshot hash does not match stored subject snapshot hash."""
    pass


class ReviewIdempotencyConflictException(Exception):
    """Raised when idempotency_key is reused with conflicting review parameters."""
    pass


class MotifReviewRepository:
    """SQLAlchemy Repository for motif review subjects and append-only audit events."""

    @staticmethod
    def get_subject_by_identity(
        db: Session,
        analysis_id: str,
        candidate_id: str
    ) -> Optional[MotifReviewSubjectModel]:
        """Lookup review subject by analysis_id and candidate_id."""
        stmt = select(MotifReviewSubjectModel).where(
            MotifReviewSubjectModel.analysis_id == analysis_id,
            MotifReviewSubjectModel.candidate_id == candidate_id
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_subject_by_public_id(
        db: Session,
        review_subject_id: str
    ) -> Optional[MotifReviewSubjectModel]:
        """Lookup review subject by public review_subject_id string (e.g. subj_...)."""
        stmt = select(MotifReviewSubjectModel).where(
            MotifReviewSubjectModel.review_subject_id == review_subject_id
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_subject_by_uuid(
        db: Session,
        subject_uuid: uuid.UUID
    ) -> Optional[MotifReviewSubjectModel]:
        """Lookup review subject by primary key UUID."""
        stmt = select(MotifReviewSubjectModel).where(
            MotifReviewSubjectModel.id == subject_uuid
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_subject(
        db: Session,
        analysis_id: str,
        candidate_id: str,
        visual_candidate_key: str,
        proposed_canonical_motif_key: Optional[str],
        original_candidate_status: str,
        candidate_confidence: float,
        candidate_snapshot: Dict[str, Any],
        snapshot_hash: str,
        model_provenance: Dict[str, Any],
        image_asset_id: Optional[str] = None,
        ontology_version: str = "motif-ontology-v1.0.0"
    ) -> MotifReviewSubjectModel:
        """
        Create a new MotifReviewSubjectModel if absent, or return existing model if present.
        """
        existing = MotifReviewRepository.get_subject_by_identity(db, analysis_id, candidate_id)
        if existing is not None:
            return existing

        review_subject_id = f"subj_{uuid.uuid4().hex[:16]}"
        subject = MotifReviewSubjectModel(
            id=uuid.uuid4(),
            review_subject_id=review_subject_id,
            analysis_id=analysis_id,
            candidate_id=candidate_id,
            image_asset_id=image_asset_id,
            visual_candidate_key=visual_candidate_key,
            proposed_canonical_motif_key=proposed_canonical_motif_key,
            original_candidate_status=original_candidate_status,
            candidate_confidence=candidate_confidence,
            candidate_snapshot=candidate_snapshot,
            snapshot_hash=snapshot_hash,
            model_provenance=model_provenance,
            ontology_version=ontology_version,
            review_version=0
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        return subject

    @staticmethod
    def append_review_event(
        db: Session,
        subject: MotifReviewSubjectModel,
        decision: str,
        resulting_status: str,
        selected_canonical_motif_key: Optional[str],
        reason_code: Optional[str],
        note: Optional[str],
        reviewer_ref: str,
        reviewer_boundary: str,
        candidate_snapshot_hash: str,
        idempotency_key: str,
        expected_version: int
    ) -> MotifReviewEventModel:
        """
        Atomically verify optimistic concurrency token via SQL compare-and-update, verify idempotency,
        verify candidate snapshot hash, increment subject review_version, and append audit event.
        """
        # 1. Snapshot hash verification
        if candidate_snapshot_hash != subject.snapshot_hash:
            raise ReviewSnapshotMismatchException(
                f"Candidate snapshot hash mismatch. Expected {subject.snapshot_hash}, got {candidate_snapshot_hash}"
            )

        # 2. Check Idempotency key BEFORE concurrency reservation
        stmt_idemp = select(MotifReviewEventModel).where(
            MotifReviewEventModel.review_subject_id == subject.id,
            MotifReviewEventModel.idempotency_key == idempotency_key
        )
        existing_event = db.execute(stmt_idemp).scalar_one_or_none()
        if existing_event is not None:
            # Verify full parameter compatibility
            if (existing_event.decision == decision and
                existing_event.resulting_status == resulting_status and
                existing_event.selected_canonical_motif_key == selected_canonical_motif_key and
                existing_event.reason_code == reason_code and
                existing_event.note == note and
                existing_event.reviewer_ref == reviewer_ref and
                existing_event.reviewer_boundary == reviewer_boundary and
                existing_event.candidate_snapshot_hash == candidate_snapshot_hash):
                return existing_event
            else:
                raise ReviewIdempotencyConflictException(
                    f"Idempotency key '{idempotency_key}' reused with conflicting decision payload."
                )

        # 3. Atomic Optimistic Concurrency Compare-and-Update (WHERE id = :id AND review_version = :expected_version)
        stmt_update = (
            update(MotifReviewSubjectModel)
            .where(
                MotifReviewSubjectModel.id == subject.id,
                MotifReviewSubjectModel.review_version == expected_version
            )
            .values(review_version=expected_version + 1)
        )
        res = db.execute(stmt_update)
        if res.rowcount == 0:
            raise ReviewConcurrencyException(
                f"Concurrency conflict: expected version {expected_version}, current subject version mismatch."
            )

        # 4. Determine supersedes relation and next version number
        latest_event = MotifReviewRepository.get_effective_event(db, subject.id)
        supersedes_id = latest_event.id if latest_event else None
        next_version = expected_version + 1

        review_id = f"rev_{uuid.uuid4().hex[:16]}"
        event = MotifReviewEventModel(
            id=uuid.uuid4(),
            review_id=review_id,
            review_subject_id=subject.id,
            decision=decision,
            resulting_status=resulting_status,
            selected_canonical_motif_key=selected_canonical_motif_key,
            reason_code=reason_code,
            note=note,
            reviewer_ref=reviewer_ref,
            reviewer_boundary=reviewer_boundary,
            candidate_snapshot_hash=candidate_snapshot_hash,
            idempotency_key=idempotency_key,
            version=next_version,
            supersedes_review_id=supersedes_id
        )

        try:
            db.add(event)
            db.commit()
            db.refresh(event)
            db.refresh(subject)
            return event
        except Exception:
            db.rollback()
            db.refresh(subject)
            raise

    @staticmethod
    def get_history(
        db: Session,
        subject_pk: uuid.UUID
    ) -> List[MotifReviewEventModel]:
        """Get all review events for a subject ordered by version ascending."""
        stmt = select(MotifReviewEventModel).where(
            MotifReviewEventModel.review_subject_id == subject_pk
        ).order_by(MotifReviewEventModel.version.asc())
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_effective_event(
        db: Session,
        subject_pk: uuid.UUID
    ) -> Optional[MotifReviewEventModel]:
        """Get latest review event with highest version number for a subject."""
        stmt = select(MotifReviewEventModel).where(
            MotifReviewEventModel.review_subject_id == subject_pk
        ).order_by(MotifReviewEventModel.version.desc()).limit(1)
        return db.execute(stmt).scalar_one_or_none()
