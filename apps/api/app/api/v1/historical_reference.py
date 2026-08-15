"""API endpoints for Historical Reference Collection v1."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.historical_reference.exceptions import HistoricalReferenceNotFoundError
from app.domain.historical_reference.schemas import (
    HistoricalReferenceListResponse,
    HistoricalReferenceDetailRead,
    HistoricalReferenceMetaResponse
)
from app.domain.historical_reference.service import HistoricalReferenceService

router = APIRouter(tags=["historical-references"])


@router.get(
    "/historical-references",
    response_model=HistoricalReferenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical reference carpet records"
)
async def list_historical_references(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    institution: Optional[str] = Query(None, description="Filter by holding museum/institution name"),
    culture: Optional[str] = Query(None, description="Filter by source-reported culture"),
    period: Optional[str] = Query(None, description="Filter by source-reported period"),
    dynasty_or_tradition: Optional[str] = Query(None, description="Filter by dynasty or tradition"),
    department: Optional[str] = Query(None, description="Filter by museum department"),
    db: AsyncSession = Depends(get_db)
) -> HistoricalReferenceListResponse:
    service = HistoricalReferenceService(db)
    return await service.list_historical_references(
        limit=limit,
        offset=offset,
        institution=institution,
        culture=culture,
        period=period,
        dynasty_or_tradition=dynasty_or_tradition,
        department=department
    )


@router.get(
    "/historical-references/{id_or_reference_key}",
    response_model=HistoricalReferenceDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get historical reference record detail with primary & supporting sources"
)
async def get_historical_reference_detail(
    id_or_reference_key: str,
    db: AsyncSession = Depends(get_db)
) -> HistoricalReferenceDetailRead:
    service = HistoricalReferenceService(db)
    try:
        return await service.get_historical_reference_detail(id_or_reference_key)
    except HistoricalReferenceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HISTORICAL_REFERENCE_NOT_FOUND", "message": str(e)}
        )


@router.get(
    "/meta/historical-references",
    response_model=HistoricalReferenceMetaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical reference collection API & schema version metadata"
)
async def get_meta_historical_references() -> HistoricalReferenceMetaResponse:
    return HistoricalReferenceService.get_meta_historical_references()
