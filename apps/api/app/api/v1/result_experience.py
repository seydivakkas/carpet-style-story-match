"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

FastAPI Endpoints for Unified 5-Card Upload Result Experience (V2-08).
"""
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, status, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.upload_analysis import UploadAnalysisModel
from app.core.config import Settings
from app.domain.result_experience.schemas import UnifiedUploadResult
from app.domain.orchestrator.service import UnifiedAnalysisOrchestrator

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
    orchestrator = UnifiedAnalysisOrchestrator(db=db, settings=settings)
    result = await orchestrator.run_analysis(
        raw_bytes=contents,
        mime_type=mime_type
    )
    return result


@router.get(
    "/{analysis_id}/unified-result",
    status_code=status.HTTP_200_OK,
    response_model=UnifiedUploadResult,
    summary="Get Unified 5-Card Result by Analysis ID from Database (Read-Only)"
)
async def get_unified_result_by_id(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> UnifiedUploadResult:
    """Fetches persisted 5-card analysis run from SQLite database."""
    stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if record and record.unified_result:
        return UnifiedUploadResult.model_validate(record.unified_result)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Analysis result not found"
    )

