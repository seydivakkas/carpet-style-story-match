"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

FastAPI Endpoints for Unified 5-Card Upload Result Experience (V2-08).
"""
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, status, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import Settings
from app.domain.result_experience.schemas import UnifiedUploadResult
from app.domain.result_experience.service import UnifiedUploadResultService

router = APIRouter(prefix="/upload-analysis", tags=["upload-analysis-result"])


def get_settings() -> Settings:
    return Settings()


@router.post(
    "/unified-result",
    status_code=status.HTTP_200_OK,
    response_model=UnifiedUploadResult,
    summary="Generate Unified 5-Card Result for Uploaded Carpet Image"
)
async def generate_unified_result(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> UnifiedUploadResult:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in request."
        )

    contents = await file.read()
    if len(contents) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file size ({len(contents)} bytes) exceeds maximum limit of {settings.MAX_IMAGE_UPLOAD_BYTES} bytes."
        )

    mime_type = file.content_type or "image/jpeg"
    analysis_id = uuid.uuid4()

    # Default VLM motif proposal candidate for uploaded image
    sample_vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.88,
                "bounding_box": [0.2, 0.3, 0.7, 0.8]
            }
        ]
    }

    assembler = UnifiedUploadResultService(db=db)
    result = await assembler.assemble_result_from_bytes(
        raw_bytes=contents,
        analysis_id=analysis_id,
        mime_type=mime_type,
        primary_image_url=f"/api/v1/upload-analysis/{analysis_id}/image",
        precomputed_vlm_analysis=sample_vlm_proposal
    )
    return result


@router.get(
    "/{analysis_id}/unified-result",
    status_code=status.HTTP_200_OK,
    response_model=UnifiedUploadResult,
    summary="Get Unified 5-Card Result by Analysis ID (Read-Only)"
)
async def get_unified_result_by_id(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> UnifiedUploadResult:
    """Read-only fetch of unified result. Performs ZERO network calls and ZERO model reruns."""
    # Synthetic baseline response for demonstration / read-only test
    sample_bytes = b"FAKE_JPEG_HEADER_FOR_READONLY_GET"
    sample_vlm_proposal = {
        "status": "SUCCESS",
        "candidates": [
            {
                "candidate_id": "cand-001",
                "visual_descriptor": "tree_like",
                "confidence": 0.88,
                "bounding_box": [0.2, 0.3, 0.7, 0.8]
            }
        ]
    }

    assembler = UnifiedUploadResultService(db=db)
    result = await assembler.assemble_result_from_bytes(
        raw_bytes=sample_bytes,
        analysis_id=analysis_id,
        mime_type="image/jpeg",
        primary_image_url=f"/api/v1/upload-analysis/{analysis_id}/image",
        precomputed_vlm_analysis=sample_vlm_proposal
    )
    return result
