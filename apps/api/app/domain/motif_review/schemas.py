"""
Domain Contract Schemas for Human Motif Review (motif-review-v1.0.0).

Strict Pydantic v2 domain DTOs for review subjects, review decisions, review events,
and effective review results.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

MOTIF_REVIEW_SCHEMA_VERSION = "motif-review-v1.0.0"


class ReviewerBoundaryEnum(str, Enum):
    """Trust boundary classification for reviewer identity provenance."""
    GATEWAY_TRUSTED = "GATEWAY_TRUSTED"
    DEVELOPMENT_ADMIN = "DEVELOPMENT_ADMIN"
    SYSTEM_IMPORT = "SYSTEM_IMPORT"


class MotifReviewReasonCode(str, Enum):
    """Controlled visual review reason codes (strictly non-cultural)."""
    VISUAL_MATCH_CONFIRMED = "VISUAL_MATCH_CONFIRMED"
    INSUFFICIENT_VISUAL_EVIDENCE = "INSUFFICIENT_VISUAL_EVIDENCE"
    AMBIGUOUS_WITH_OTHER_MOTIF = "AMBIGUOUS_WITH_OTHER_MOTIF"
    REGION_INCORRECT = "REGION_INCORRECT"
    ONTOLOGY_MAPPING_INCORRECT = "ONTOLOGY_MAPPING_INCORRECT"
    NOT_A_MOTIF = "NOT_A_MOTIF"
    CROP_OR_OCCLUSION_LIMITATION = "CROP_OR_OCCLUSION_LIMITATION"
    OTHER = "OTHER"


class ReviewDecisionEnum(str, Enum):
    """Allowed human curator decisions."""
    CONFIRM = "CONFIRM"
    UNCERTAIN = "UNCERTAIN"
    REJECT = "REJECT"


class ReviewResultingStatusEnum(str, Enum):
    """Server-owned resulting trusted candidate status."""
    CURATOR_CONFIRMED = "CURATOR_CONFIRMED"
    UNCERTAIN = "UNCERTAIN"
    REJECTED = "REJECTED"


class ResearchEligibilityEnum(str, Enum):
    """Source research eligibility resulting from human review."""
    SOURCE_RESEARCH_ALLOWED = "SOURCE_RESEARCH_ALLOWED"
    SOURCE_RESEARCH_BLOCKED = "SOURCE_RESEARCH_BLOCKED"


class MotifReviewSubject(BaseModel):
    """Immutable representation of an AI motif candidate snapshot subject."""
    model_config = ConfigDict(extra="forbid")

    review_subject_id: str = Field(description="Stable server-assigned public subject ID (e.g. subj_...)")
    analysis_id: str = Field(description="User upload analysis ID")
    candidate_id: str = Field(description="AI candidate ID within analysis")
    image_asset_id: Optional[str] = Field(default=None, description="Optional safe image asset reference")
    visual_candidate_key: str = Field(description="V2-02 visual candidate key")
    proposed_canonical_motif_key: Optional[str] = Field(default=None, description="Proposed canonical motif key if mapped")
    original_candidate_status: str = Field(description="Original AI candidate status (e.g. AI_CANDIDATE)")
    candidate_confidence: float = Field(ge=0.0, le=1.0, description="Model self-reported confidence")
    candidate_snapshot: Dict[str, Any] = Field(description="Canonical reviewed candidate snapshot dictionary")
    snapshot_hash: str = Field(min_length=64, max_length=64, description="SHA-256 hash of candidate snapshot")
    model_provenance: Dict[str, Any] = Field(description="AI model provenance metadata")
    ontology_version: str = Field(default="motif-ontology-v1.0.0", description="Motif ontology version")
    review_version: int = Field(default=0, ge=0, description="Optimistic concurrency version token")
    created_at: datetime = Field(description="Subject registration timestamp")


class MotifReviewDecisionRequest(BaseModel):
    """Client request to submit a human curator decision on a review subject."""
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecisionEnum = Field(description="Curator decision: CONFIRM, UNCERTAIN, or REJECT")
    selected_canonical_motif_key: Optional[str] = Field(default=None, description="Canonical motif key (required for CONFIRM)")
    reason_code: Optional[MotifReviewReasonCode] = Field(default=None, description="Controlled non-cultural reason code")
    note: Optional[str] = Field(default=None, max_length=1000, description="Operational curator note (max 1000 chars)")
    reviewer_ref: str = Field(min_length=1, max_length=255, description="Reviewer reference ID or username")
    reviewer_boundary: ReviewerBoundaryEnum = Field(description="Trust boundary classification (MUST be explicitly supplied by trusted server context)")
    expected_version: int = Field(ge=0, description="Expected concurrency review_version token of subject")
    idempotency_key: str = Field(min_length=1, max_length=100, description="Unique idempotency key for this review request")


class MotifReviewEvent(BaseModel):
    """Append-only audit trail record for a single human review decision."""
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(description="Stable server-assigned public review ID (e.g. rev_...)")
    review_subject_id: str = Field(description="Parent review subject UUID string")
    decision: ReviewDecisionEnum = Field(description="Human decision")
    resulting_status: ReviewResultingStatusEnum = Field(description="Server-computed trusted status")
    selected_canonical_motif_key: Optional[str] = Field(default=None, description="Selected canonical motif key if confirmed")
    reason_code: Optional[MotifReviewReasonCode] = Field(default=None, description="Controlled reason code")
    note: Optional[str] = Field(default=None, description="Curator note")
    reviewer_ref: str = Field(description="Reviewer reference")
    reviewer_boundary: ReviewerBoundaryEnum = Field(description="Reviewer trust boundary")
    candidate_snapshot_hash: str = Field(description="SHA-256 candidate snapshot hash verified at review time")
    idempotency_key: str = Field(description="Persisted idempotency key")
    version: int = Field(ge=1, description="Sequential review event version for subject")
    supersedes_review_id: Optional[str] = Field(default=None, description="Prior review event ID superseded if re-reviewed")
    created_at: datetime = Field(description="Event timestamp")


class MotifReviewResult(BaseModel):
    """Effective review state and research eligibility response."""
    model_config = ConfigDict(extra="forbid")

    review_version_schema: str = Field(default=MOTIF_REVIEW_SCHEMA_VERSION)
    subject: MotifReviewSubject = Field(description="Candidate review subject")
    effective_event: Optional[MotifReviewEvent] = Field(default=None, description="Latest effective review event if reviewed")
    effective_status: str = Field(description="Effective candidate status (AI_CANDIDATE or resulting status)")
    research_eligibility: ResearchEligibilityEnum = Field(description="Research eligibility (SOURCE_RESEARCH_ALLOWED or BLOCKED)")
    history_count: int = Field(ge=0, description="Total review events in subject audit trail")


class MotifReviewDecisionClientBody(BaseModel):
    """Client decision request body for POST /api/v1/reviews/motif-candidates/{id}/decision."""
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecisionEnum = Field(description="Curator decision: CONFIRM, UNCERTAIN, or REJECT")
    selected_canonical_motif_key: Optional[str] = Field(default=None, description="Canonical motif key (required for CONFIRM)")
    reason_code: Optional[MotifReviewReasonCode] = Field(default=None, description="Controlled non-cultural reason code")
    note: Optional[str] = Field(default=None, max_length=1000, description="Operational curator note (max 1000 chars)")
    expected_version: int = Field(ge=0, description="Expected concurrency review_version token of subject")


class MotifReviewQueueItemResponse(BaseModel):
    """Summary item representation for curator review queue API."""
    model_config = ConfigDict(extra="forbid")

    review_subject_id: str
    analysis_id: str
    candidate_id: str
    visual_candidate_key: str
    proposed_canonical_motif_key: Optional[str] = None
    original_candidate_status: str
    candidate_confidence: float
    created_at: datetime
    effective_status: str
    review_version: int
    research_eligibility: ResearchEligibilityEnum
    image_url: Optional[str] = None


class MotifReviewQueuePaginatedResponse(BaseModel):
    """Paginated response for review queue API."""
    model_config = ConfigDict(extra="forbid")

    items: List[MotifReviewQueueItemResponse]
    total_count: int
    limit: int
    offset: int
    status_filter: Optional[str] = None


class MotifReviewDetailResponse(BaseModel):
    """Full detail representation for candidate review screen."""
    model_config = ConfigDict(extra="forbid")

    review_subject_id: str
    analysis_id: str
    candidate_id: str
    visual_candidate_key: str
    proposed_canonical_motif_key: Optional[str] = None
    original_candidate_status: str
    candidate_confidence: float
    candidate_region: Dict[str, Any]
    visual_evidence: List[str]
    model_provenance: Dict[str, Any]
    snapshot_hash: str
    ontology_version: str
    review_version: int
    created_at: datetime
    effective_status: str
    research_eligibility: ResearchEligibilityEnum
    history_count: int
    effective_event: Optional[MotifReviewEvent] = None
    image_url: Optional[str] = None
    image_available: bool = False

