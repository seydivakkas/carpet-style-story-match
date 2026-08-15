"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Liveness & Readiness Health Endpoints v1.
- GET /health / GET /health/live: Liveness check (process alive)
- GET /health/ready: Readiness check (DB & Storage connectivity)
"""
import os
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    database: str
    storage: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check endpoint")
@router.get("/health/live", response_model=HealthResponse, summary="Liveness check endpoint")
async def health_check():
    """Liveness probe: verifies the API process is running."""
    return HealthResponse(
        status="ok",
        service="carpet-style-story-match-api"
    )


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness check endpoint")
async def readiness_check(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Readiness probe: verifies database connectivity and storage readiness
    before serving production traffic.
    """
    db_healthy = False
    storage_healthy = False

    # 1. Verify DB Query
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_healthy = True
    except Exception:
        db_healthy = False

    # 2. Verify Storage Accessibility
    try:
        if settings.STORAGE_BACKEND.lower() == "local":
            storage_path = os.path.abspath(settings.IMAGE_STORAGE_ROOT)
            os.makedirs(storage_path, exist_ok=True)
            if os.path.exists(storage_path) and os.access(storage_path, os.W_OK):
                storage_healthy = True
        elif settings.STORAGE_BACKEND.lower() == "s3":
            # For S3, verify bucket configured
            if settings.S3_BUCKET_NAME:
                storage_healthy = True
        else:
            storage_healthy = True
    except Exception:
        storage_healthy = False

    is_ready = db_healthy and storage_healthy
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        service="carpet-style-story-match-api",
        database="healthy" if db_healthy else "unhealthy",
        storage="healthy" if storage_healthy else "unhealthy"
    )
