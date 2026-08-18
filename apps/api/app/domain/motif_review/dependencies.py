"""
FastAPI dependencies for Human Motif Review Access & Reviewer Context (V2-06B).

Provides fail-closed access mode verification (DISABLED, DEVELOPMENT_ADMIN, GATEWAY_TRUSTED).
"""
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from app.domain.motif_review.schemas import ReviewerBoundaryEnum


class ReviewerContext(BaseModel):
    """Server-owned verified reviewer context."""
    model_config = ConfigDict(extra="forbid")

    reviewer_ref: str
    reviewer_boundary: ReviewerBoundaryEnum


def get_reviewer_context(
    request: Request
) -> ReviewerContext:
    """
    FastAPI dependency that enforces review access policy and returns server-owned ReviewerContext.
    
    Fails closed if access is DISABLED, if DEVELOPMENT_ADMIN is attempted in production,
    or if GATEWAY_TRUSTED is requested without verified server gateway middleware.
    """
    mode = (settings.MOTIF_REVIEW_ACCESS_MODE or "DISABLED").strip().upper()

    if mode == "DISABLED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "REVIEW_ACCESS_DISABLED",
                "message": "Human motif review access is disabled in current environment."
            }
        )
    elif mode == "DEVELOPMENT_ADMIN":
        if (settings.APP_ENV or "development").strip().lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "REVIEW_ACCESS_DISABLED",
                    "message": "DEVELOPMENT_ADMIN access mode is forbidden in production environment."
                }
            )
        reviewer_ref = (settings.MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF or "").strip()
        if not reviewer_ref:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "REVIEW_ACCESS_DISABLED",
                    "message": "DEVELOPMENT_ADMIN access mode requires an explicit non-empty MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF server configuration."
                }
            )
        if len(reviewer_ref) > 100:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "REVIEW_ACCESS_DISABLED",
                    "message": "MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF exceeds maximum length of 100 characters."
                }
            )
        return ReviewerContext(
            reviewer_ref=reviewer_ref,
            reviewer_boundary=ReviewerBoundaryEnum.DEVELOPMENT_ADMIN
        )
    elif mode == "GATEWAY_TRUSTED":
        # Check if trusted server gateway verified state exists
        verified_ref = getattr(request.state, "verified_reviewer_ref", None)
        if verified_ref:
            return ReviewerContext(
                reviewer_ref=verified_ref,
                reviewer_boundary=ReviewerBoundaryEnum.GATEWAY_TRUSTED
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "REVIEW_ACCESS_DISABLED",
                    "message": "GATEWAY_TRUSTED access mode requires a verified server gateway context."
                }
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "REVIEW_ACCESS_DISABLED",
                "message": f"Unknown review access mode '{mode}'."
            }
        )
