"""
User Upload Visual Analysis & Motif Detection API Endpoints (V2-03).

Provides real backend VLM inference capabilities over user uploaded carpet images.
Strictly validates visual contracts, handles provider statuses, and guarantees zero cultural claims.
"""
import uuid
from fastapi import APIRouter, File, UploadFile, status, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import Settings
from app.domain.upload_analysis.schemas import UploadAnalysisResult
from app.domain.upload_analysis.image_preparation import ImageValidationError
from app.domain.upload_analysis.vlm_provider import (
    VLMProviderError,
    VLMAuthError,
    VLMTimeoutError,
    VLMMalformedOutputError
)
from app.domain.upload_analysis.service import (
    get_vlm_provider_status,
    analyze_user_upload_image
)

router = APIRouter(prefix="/upload-analysis", tags=["upload-analysis"])


def get_settings() -> Settings:
    return Settings()


@router.get(
    "/provider-status",
    status_code=status.HTTP_200_OK,
    summary="Get VLM Provider Configuration & Status"
)
async def get_provider_status(
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    return await get_vlm_provider_status(settings)


@router.post(
    "/motif-detect",
    status_code=status.HTTP_200_OK,
    response_model=UploadAnalysisResult,
    summary="Perform Visual Motif & Category Detection on Uploaded Carpet Image"
)
async def detect_motifs(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
) -> UploadAnalysisResult:
    # Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in request."
        )

    # Check file size bound
    contents = await file.read()
    if len(contents) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file size ({len(contents)} bytes) exceeds maximum limit of {settings.MAX_IMAGE_UPLOAD_BYTES} bytes."
        )

    mime_type = file.content_type or "image/jpeg"

    try:
        result = await analyze_user_upload_image(
            raw_bytes=contents,
            mime_type=mime_type,
            settings=settings
        )
        return result
    except ImageValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {e}"
        )
    except VLMAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"VLM Provider authorization error: {e}"
        )
    except VLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"VLM Provider request timed out: {e}"
        )
    except VLMMalformedOutputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"VLM Provider returned invalid structured output: {e}"
        )
    except VLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"VLM Provider error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during visual inference: {e}"
        )


@router.get(
    "/{analysis_id}/image",
    status_code=status.HTTP_200_OK,
    summary="Get Binary Image Content of Uploaded Analysis Run"
)
async def get_analysis_image(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import Response
    from sqlalchemy import select
    from app.db.models.upload_analysis import UploadAnalysisModel
    from app.domain.images.storage import LocalImageStorage

    stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if not record or not record.image_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for analysis '{analysis_id}' not found."
        )

    storage = LocalImageStorage()
    try:
        image_bytes = storage.get_image_bytes(record.image_path)
        return Response(content=image_bytes, media_type=record.mime_type or "image/jpeg")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image file content unavailable: {e}"
        )


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Uploaded Carpet Analysis and Associated Review Records"
)
async def delete_analysis_record(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    import os
    import logging
    from sqlalchemy import select, delete
    from app.db.models.upload_analysis import UploadAnalysisModel
    from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
    from app.domain.images.storage import LocalImageStorage

    logger = logging.getLogger(__name__)

    # 1. Find analysis record
    stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if record and record.image_path:
        try:
            storage = LocalImageStorage()
            storage.delete_image(record.image_path)
        except Exception as e:
            logger.exception("Analysis image deletion failed for %s", analysis_id)
            raise HTTPException(status_code=500, detail="Görsel silinemedi; analiz kaydı korunuyor.") from e

    # 2. Find and delete review subjects & events
    aid_str = str(analysis_id)
    stmt_subj = select(MotifReviewSubjectModel).where(
        MotifReviewSubjectModel.analysis_id == aid_str
    )
    res_subj = await db.execute(stmt_subj)
    subjects = res_subj.scalars().all()

    for subj in subjects:
        await db.execute(
            delete(MotifReviewEventModel).where(
                MotifReviewEventModel.review_subject_id == subj.id
            )
        )
        await db.delete(subj)

    if record:
        await db.delete(record)

    await db.commit()

    return {
        "status": "success",
        "message": f"Analysis {analysis_id} and all related review records deleted successfully.",
        "analysis_id": str(analysis_id)
    }



