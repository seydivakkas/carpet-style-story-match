"""
User Upload Visual Analysis & Motif Detection API Endpoints (V2-03).

Provides real backend VLM inference capabilities over user uploaded carpet images.
Strictly validates visual contracts, handles provider statuses, and guarantees zero cultural claims.
"""
from fastapi import APIRouter, File, UploadFile, status, HTTPException, Depends
from typing import Dict, Any

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
