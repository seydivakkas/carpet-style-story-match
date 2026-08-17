"""
Database ORM models for Human Motif Review Persistence v1 (motif-review-v1.0.0).

Defines durable persistence for AI motif candidate snapshots and append-only
human review audit events.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class MotifReviewSubjectModel(Base):
    """
    Persisted immutable identity and semantic snapshot of an AI motif candidate.
    
    Includes optimistic concurrency token `review_version`.
    """

    __tablename__ = "motif_review_subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    review_subject_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    analysis_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    image_asset_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    visual_candidate_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    proposed_canonical_motif_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    original_candidate_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    candidate_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    candidate_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )
    snapshot_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    model_provenance: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )
    ontology_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="motif-ontology-v1.0.0"
    )
    review_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now()
    )

    review_events: Mapped[List["MotifReviewEventModel"]] = relationship(
        "MotifReviewEventModel",
        back_populates="review_subject",
        foreign_keys="[MotifReviewEventModel.review_subject_id]"
    )

    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "candidate_id",
            name="uq_motif_review_subject_identity"
        ),
    )


class MotifReviewEventModel(Base):
    """
    Append-only audit event recording a human curator decision on a motif candidate.
    
    FORBIDS cascade deletion (ondelete="RESTRICT") to protect audit trail integrity.
    """

    __tablename__ = "motif_review_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    review_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    review_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motif_review_subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    resulting_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )
    selected_canonical_motif_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    reason_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    reviewer_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    reviewer_boundary: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    candidate_snapshot_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    supersedes_review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motif_review_events.id", ondelete="RESTRICT"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now()
    )

    review_subject: Mapped["MotifReviewSubjectModel"] = relationship(
        "MotifReviewSubjectModel",
        back_populates="review_events",
        foreign_keys=[review_subject_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "review_subject_id",
            "idempotency_key",
            name="uq_motif_review_event_idempotency"
        ),
        UniqueConstraint(
            "review_subject_id",
            "version",
            name="uq_motif_review_event_version"
        ),
    )
