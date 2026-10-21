"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

FastAPI Endpoints for Unified 5-Card Upload Result Experience & Async Polling (V2-08 & Phase P5).
"""
import uuid
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, status, HTTPException, Depends, BackgroundTasks, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session_module
from app.db.session import get_db
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum
from app.core.config import Settings
from app.domain.result_experience.access_control import new_analysis_access_token, require_analysis_access
from app.domain.images.storage import LocalImageStorage
from app.domain.result_experience.schemas import (
    UnifiedUploadResult,
    AcceptedAnalysisResponse,
    AnalysisStatusResponse,
)
from app.domain.orchestrator.service import UnifiedAnalysisOrchestrator
from app.domain.result_experience.service import UnifiedUploadResultService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload-analysis", tags=["upload-analysis-result"])


def get_settings() -> Settings:
    return Settings()


async def run_background_analysis(
    analysis_id: uuid.UUID,
    raw_bytes: bytes,
    mime_type: str,
    settings: Settings
):
    """Background worker creating its own AsyncSession to execute orchestrator pipeline."""
    async with db_session_module.AsyncSessionLocal() as bg_db:
        orchestrator = UnifiedAnalysisOrchestrator(db=bg_db, settings=settings)
        try:
            out_res = await orchestrator.run_analysis(
                raw_bytes=raw_bytes,
                mime_type=mime_type,
                analysis_id=analysis_id
            )
            logger.info(f"Background analysis completed for correlation_id={analysis_id}, state={out_res.visual_character.state}")
        except Exception as e:
            logger.error(f"Background analysis failed for correlation_id={analysis_id}: {e}", exc_info=True)
            try:
                stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
                res = await bg_db.execute(stmt)
                record = res.scalar_one_or_none()
                if not record:
                    record = UploadAnalysisModel(
                        id=analysis_id,
                        original_sha256="error_state",
                        mime_type=mime_type,
                        quality_status="FAIL",
                        status=UploadAnalysisStatusEnum.FAILED,
                        error=str(e)
                    )
                    bg_db.add(record)
                else:
                    record.status = UploadAnalysisStatusEnum.FAILED
                    record.error = str(e)
                await bg_db.commit()
            except Exception as db_err:
                logger.error(f"Failed to set FAILED status in DB for {analysis_id}: {db_err}")


@router.post(
    "/unified-result",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AcceptedAnalysisResponse,
    summary="Accept Carpet Image Upload and Enqueue Background 5-Card Analysis",
    description="Validates image file size, persists raw image to disk, creates initial PROCESSING record, and enqueues background processing. Returns 202 Accepted with poll URL."
)
async def generate_unified_result(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
) -> AcceptedAnalysisResponse:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in request."
        )

    # Dosyanın tamamını okumadan önce limit uygulanır.
    parts = []
    received = 0
    while chunk := await file.read(1024 * 1024):
        received += len(chunk)
        if received > settings.MAX_IMAGE_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image exceeds configured upload size limit."
            )
        parts.append(chunk)
    contents = b"".join(parts)

    mime_type = file.content_type or "image/jpeg"
    aid = uuid.uuid4()
    access_token, owner_token_sha256 = new_analysis_access_token()

    # Ham görüntü diske yazılmaz. İşçi doğrulama ve EXIF temizliği
    # sonrasında normalize edilmiş görüntüyü kaydeder.
    # Persist initial PROCESSING record with standalone session
    async with db_session_module.AsyncSessionLocal() as post_db:
        initial_record = UploadAnalysisModel(
            id=aid,
            owner_token_sha256=owner_token_sha256,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.ANALYSIS_RETENTION_DAYS),
            original_sha256="pending_computation",
            image_path=None,
            mime_type=mime_type,
            quality_status="PENDING",
            status=UploadAnalysisStatusEnum.PROCESSING
        )
        post_db.add(initial_record)
        await post_db.commit()

    # Schedule async background task
    background_tasks.add_task(
        run_background_analysis,
        analysis_id=aid,
        raw_bytes=contents,
        mime_type=mime_type,
        settings=settings
    )

    return AcceptedAnalysisResponse(
        access_token=access_token,
        analysis_id=aid,
        status="PROCESSING",
        poll_url=f"/api/v1/upload-analysis/{aid}/status"
    )


@router.get(
    "/{analysis_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=AnalysisStatusResponse,
    summary="Get Analysis Status for Polling (Read-Only)",
    description="Returns current status of analysis run: PROCESSING, COMPLETED, BLOCKED_BY_QUALITY, or FAILED."
)
async def get_analysis_status(
    analysis_id: uuid.UUID,
    x_analysis_token: Optional[str] = Header(None, alias="X-Analysis-Token"),
    db: AsyncSession = Depends(get_db)
) -> AnalysisStatusResponse:
    stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    require_analysis_access(record, x_analysis_token)

    return AnalysisStatusResponse(
        analysis_id=record.id,
        status=record.status.value if hasattr(record.status, "value") else str(record.status),
        error=record.error
    )


@router.get(
    "/{analysis_id}/unified-result",
    status_code=status.HTTP_200_OK,
    response_model=UnifiedUploadResult,
    summary="Get Unified 5-Card Result by Analysis ID from Database (Read-Only)",
    description="Fetches persisted 5-card analysis run from database once status is COMPLETED or BLOCKED_BY_QUALITY. Returns 409 Conflict if still processing or failed."
)
async def get_unified_result_by_id(
    analysis_id: uuid.UUID,
    x_analysis_token: Optional[str] = Header(None, alias="X-Analysis-Token"),
    db: AsyncSession = Depends(get_db)
) -> UnifiedUploadResult:
    """Fetches persisted 5-card analysis run from database."""
    stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if record is None:
        # Var olmayan kayıt sözleşmesinin 404 detayını koru; mevcut kayıtta erişim zorunlu.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis result not found")
    require_analysis_access(record, x_analysis_token)

    status_val = record.status.value if hasattr(record.status, "value") else str(record.status)

    if status_val in ("COMPLETED", "BLOCKED_BY_QUALITY"):
        if record.unified_result:
            try:
                result_service = UnifiedUploadResultService(db=db)
                refreshed_dict = await result_service.refresh_unified_result_with_reviews(
                    analysis_id=analysis_id,
                    current_dict=record.unified_result
                )
                # GET isteği veritabanı durumunu değiştirmemeli.
                return UnifiedUploadResult.model_validate(refreshed_dict)
            except Exception as e:
                logger.warning(f"Fallback to raw snapshot due to refresh error: {e}")
                return UnifiedUploadResult.model_validate(record.unified_result)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result snapshot missing"
        )

    if status_val == "PROCESSING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis still processing"
        )

    if status_val == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=record.error or "Analysis failed"
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Analysis result not found"
    )
