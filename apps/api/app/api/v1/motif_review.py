"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-06B Protected Human Motif Review API Router.

Provides protected endpoints for review queue listing, candidate detail inspection,
audit event history, and curator decision submission.
"""
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.db.session import get_db
from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
from app.domain.motif_review.dependencies import ReviewerContext, get_reviewer_context
from app.domain.motif_review.schemas import (
    MotifReviewSubject,
    MotifReviewDecisionRequest,
    MotifReviewDecisionClientBody,
    MotifReviewEvent,
    MotifReviewResult,
    MotifReviewQueueItemResponse,
    MotifReviewQueuePaginatedResponse,
    MotifReviewDetailResponse,
    ReviewDecisionEnum,
    ReviewResultingStatusEnum,
    ResearchEligibilityEnum,
    ReviewerBoundaryEnum,
    MotifReviewReasonCode
)
from app.domain.motif_review.service import (
    MotifReviewPersistenceService,
    InvalidReviewTransitionException,
    UnknownCanonicalMotifException
)
from app.domain.motif_review.repository import (
    MotifReviewRepository,
    ReviewConcurrencyException,
    ReviewSnapshotMismatchException,
    ReviewIdempotencyConflictException
)

router = APIRouter(prefix="/reviews/motif-candidates", tags=["Human Motif Review"])


def _resolve_protected_image_url(review_subject_id: str, image_asset_id: Optional[str]) -> Tuple[Optional[str], bool]:
    """Generates the protected HTTP relative image URL for client preview bound to subject ID resource boundary."""
    if not image_asset_id:
        return None, False
    return f"/api/v1/reviews/motif-candidates/{review_subject_id}/image", True


@router.get(
    "",
    response_model=MotifReviewQueuePaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get protected motif candidate review queue"
)
async def get_review_queue(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: PENDING, CONFIRMED, UNCERTAIN, REJECTED, ALL"),
    limit: int = Query(50, ge=1, le=100, description="Max page size (max 100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    reviewer_ctx: ReviewerContext = Depends(get_reviewer_context),
    db: AsyncSession = Depends(get_db)
) -> MotifReviewQueuePaginatedResponse:
    """Returns protected review queue with deterministic status filtering and pagination."""
    clean_filter = status_filter.strip().upper() if status_filter else None
    if clean_filter is not None and clean_filter not in ("PENDING", "CONFIRMED", "UNCERTAIN", "REJECTED", "ALL"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_STATUS_FILTER",
                "message": f"Invalid status filter '{status_filter}'. Allowed values: PENDING, CONFIRMED, UNCERTAIN, REJECTED, ALL."
            }
        )

    sync_db = db.sync_session
    service = MotifReviewPersistenceService(sync_db)

    # 1. Fetch all subjects ordered by created_at ASC
    stmt = select(MotifReviewSubjectModel).order_by(MotifReviewSubjectModel.created_at.asc())
    result = await db.execute(stmt)
    all_subjects = list(result.scalars().all())

    # 2. Filter subjects by effective status in memory
    filtered_items: List[MotifReviewQueueItemResponse] = []

    for subj_model in all_subjects:
        res = service.get_effective_result_by_identity(subj_model.analysis_id, subj_model.candidate_id)
        effective_stat = res.effective_status  # AI_CANDIDATE / UNMAPPED_MOTIF_CANDIDATE, CURATOR_CONFIRMED, UNCERTAIN, REJECTED

        # Map filter categories
        matches = False
        if clean_filter is None or clean_filter == "ALL":
            matches = True
        elif clean_filter == "PENDING" and effective_stat in ("AI_CANDIDATE", "UNMAPPED_MOTIF_CANDIDATE"):
            matches = True
        elif clean_filter == "CONFIRMED" and effective_stat == ReviewResultingStatusEnum.CURATOR_CONFIRMED.value:
            matches = True
        elif clean_filter == "UNCERTAIN" and effective_stat == ReviewResultingStatusEnum.UNCERTAIN.value:
            matches = True
        elif clean_filter == "REJECTED" and effective_stat == ReviewResultingStatusEnum.REJECTED.value:
            matches = True

        if matches:
            img_url, _ = _resolve_protected_image_url(subj_model.review_subject_id, subj_model.image_asset_id)
            item = MotifReviewQueueItemResponse(
                review_subject_id=subj_model.review_subject_id,
                analysis_id=subj_model.analysis_id,
                candidate_id=subj_model.candidate_id,
                visual_candidate_key=subj_model.visual_candidate_key,
                proposed_canonical_motif_key=subj_model.proposed_canonical_motif_key,
                original_candidate_status=subj_model.original_candidate_status,
                candidate_confidence=subj_model.candidate_confidence,
                created_at=subj_model.created_at,
                effective_status=effective_stat,
                review_version=subj_model.review_version,
                research_eligibility=res.research_eligibility,
                image_url=img_url
            )
            filtered_items.append(item)

    total_count = len(filtered_items)
    paginated_items = filtered_items[offset:offset + limit]

    return MotifReviewQueuePaginatedResponse(
        items=paginated_items,
        total_count=total_count,
        limit=limit,
        offset=offset,
        status_filter=clean_filter
    )


@router.get(
    "/{review_subject_id}",
    response_model=MotifReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get protected detailed review object for a motif candidate subject"
)
async def get_review_detail(
    review_subject_id: str,
    reviewer_ctx: ReviewerContext = Depends(get_reviewer_context),
    db: AsyncSession = Depends(get_db)
) -> MotifReviewDetailResponse:
    """Returns candidate region evidence, visual observations, provenance, and effective review state."""
    sync_db = db.sync_session
    subject_model = MotifReviewRepository.get_subject_by_public_id(sync_db, review_subject_id)
    if subject_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REVIEW_SUBJECT_NOT_FOUND",
                "message": f"Review subject '{review_subject_id}' not found."
            }
        )

    service = MotifReviewPersistenceService(sync_db)
    res = service.get_effective_result_by_identity(subject_model.analysis_id, subject_model.candidate_id)
    img_url, img_avail = _resolve_protected_image_url(subject_model.review_subject_id, subject_model.image_asset_id)

    snapshot = subject_model.candidate_snapshot
    region = snapshot.get("region", {})
    visual_evidence = snapshot.get("visual_evidence", [])

    return MotifReviewDetailResponse(
        review_subject_id=subject_model.review_subject_id,
        analysis_id=subject_model.analysis_id,
        candidate_id=subject_model.candidate_id,
        visual_candidate_key=subject_model.visual_candidate_key,
        proposed_canonical_motif_key=subject_model.proposed_canonical_motif_key,
        original_candidate_status=subject_model.original_candidate_status,
        candidate_confidence=subject_model.candidate_confidence,
        candidate_region=region,
        visual_evidence=visual_evidence,
        model_provenance=subject_model.model_provenance,
        snapshot_hash=subject_model.snapshot_hash,
        ontology_version=subject_model.ontology_version,
        review_version=subject_model.review_version,
        created_at=subject_model.created_at,
        effective_status=res.effective_status,
        research_eligibility=res.research_eligibility,
        history_count=res.history_count,
        effective_event=res.effective_event,
        image_url=img_url,
        image_available=img_avail
    )


@router.get(
    "/{review_subject_id}/image",
    status_code=status.HTTP_200_OK,
    summary="Get protected review image preview asset for a candidate subject"
)
async def get_review_image(
    review_subject_id: str,
    reviewer_ctx: ReviewerContext = Depends(get_reviewer_context),
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """
    Returns the protected candidate preview image asset.
    
    Authorizes access via ReviewerContext dependency. Obtains image_asset_id
    strictly from server-persisted MotifReviewSubjectModel (no client path override).
    Enforces filesystem containment and MIME media type validation.
    """
    sync_db = db.sync_session
    subject_model = MotifReviewRepository.get_subject_by_public_id(sync_db, review_subject_id)
    if subject_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REVIEW_SUBJECT_NOT_FOUND",
                "message": f"Review subject '{review_subject_id}' not found."
            }
        )

    image_asset_id = subject_model.image_asset_id
    if not image_asset_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "IMAGE_NOT_AVAILABLE",
                "message": f"Image asset is not available for review subject '{review_subject_id}'."
            }
        )

    # File resolution & storage containment check
    safe_filename = Path(image_asset_id).name
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "IMAGE_NOT_AVAILABLE",
                "message": "Invalid asset filename."
            }
        )

    upload_root = Path(settings.IMAGE_STORAGE_ROOT).resolve()
    clean_key = image_asset_id.lstrip("/\\")
    target_path = (upload_root / clean_key).resolve()

    try:
        if not target_path.exists() or not target_path.is_file() or not target_path.is_relative_to(upload_root):
            target_path = (upload_root / safe_filename).resolve()

        if not target_path.exists() or not target_path.is_file() or not target_path.is_relative_to(upload_root):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "IMAGE_NOT_AVAILABLE",
                    "message": f"Image file for subject '{review_subject_id}' not found on storage."
                }
            )
    except (ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "IMAGE_NOT_AVAILABLE",
                "message": "Storage containment violation."
            }
        )

    # Media Type Validation (Images ONLY)
    ext = target_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }
    if ext not in mime_map:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"File type '{ext}' is not a supported review image media format."
            }
        )

    return FileResponse(
        path=str(target_path),
        media_type=mime_map[ext],
        headers={"Cache-Control": "private, max-age=3600"}
    )


@router.get(
    "/{review_subject_id}/history",
    response_model=List[MotifReviewEvent],
    status_code=status.HTTP_200_OK,
    summary="Get append-only review event history for a subject"
)
async def get_review_history(
    review_subject_id: str,
    reviewer_ctx: ReviewerContext = Depends(get_reviewer_context),
    db: AsyncSession = Depends(get_db)
) -> List[MotifReviewEvent]:
    """Returns chronological audit history for a review subject."""
    sync_db = db.sync_session
    subject_model = MotifReviewRepository.get_subject_by_public_id(sync_db, review_subject_id)
    if subject_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REVIEW_SUBJECT_NOT_FOUND",
                "message": f"Review subject '{review_subject_id}' not found."
            }
        )

    service = MotifReviewPersistenceService(sync_db)
    events = service.get_history_by_identity(subject_model.analysis_id, subject_model.candidate_id)
    return events


@router.post(
    "/{review_subject_id}/decision",
    response_model=MotifReviewResult,
    status_code=status.HTTP_200_OK,
    summary="Submit a human curator decision for a motif candidate subject"
)
async def submit_review_decision_endpoint(
    review_subject_id: str,
    body: MotifReviewDecisionClientBody,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=100, description="Unique idempotency key for this review submission"),
    reviewer_ctx: ReviewerContext = Depends(get_reviewer_context),
    db: AsyncSession = Depends(get_db)
) -> MotifReviewResult:
    """
    Submits a curator review decision (CONFIRM, UNCERTAIN, or REJECT).
    
    Uses server-owned reviewer context (reviewer_ref, reviewer_boundary) and enforces
    optimistic concurrency (expected_version) and idempotency.
    """
    sync_db = db.sync_session
    subject_model = MotifReviewRepository.get_subject_by_public_id(sync_db, review_subject_id)
    if subject_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REVIEW_SUBJECT_NOT_FOUND",
                "message": f"Review subject '{review_subject_id}' not found."
            }
        )

    # Construct strict server-side domain request with server-owned reviewer context
    domain_req = MotifReviewDecisionRequest(
        decision=body.decision,
        selected_canonical_motif_key=body.selected_canonical_motif_key,
        reason_code=body.reason_code,
        note=body.note,
        expected_version=body.expected_version,
        reviewer_ref=reviewer_ctx.reviewer_ref,
        reviewer_boundary=reviewer_ctx.reviewer_boundary,
        idempotency_key=idempotency_key
    )

    service = MotifReviewPersistenceService(sync_db)
    try:
        result = service.submit_review_decision(
            analysis_id=subject_model.analysis_id,
            candidate_id=subject_model.candidate_id,
            request=domain_req
        )
        return result
    except ReviewConcurrencyException as rce:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REVIEW_CONFLICT",
                "message": str(rce)
            }
        )
    except ReviewIdempotencyConflictException as rice:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REVIEW_IDEMPOTENCY_CONFLICT",
                "message": str(rice)
            }
        )
    except ReviewSnapshotMismatchException as rsme:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "STALE_REVIEW_SUBJECT",
                "message": str(rsme)
            }
        )
    except InvalidReviewTransitionException as irte:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_REVIEW_TRANSITION",
                "message": str(irte)
            }
        )
    except UnknownCanonicalMotifException as ucme:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNKNOWN_CANONICAL_MOTIF",
                "message": str(ucme)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"An error occurred while persisting review decision: {e}"
            }
        )
