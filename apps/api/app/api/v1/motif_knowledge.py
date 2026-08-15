"""API endpoints for Curated Motif Story + Source Provenance v1 (Read-Only)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.motif_knowledge import MotifStoryStatusEnum
from app.domain.motif_knowledge.exceptions import (
    MotifNotFoundError,
    ClaimNotFoundError,
    SourceNotFoundError,
)
from app.domain.motif_knowledge.schemas import (
    MotifRead,
    MotifListResponse,
    MotifStoryClaimRead,
    MotifStoryClaimListResponse,
    CuratedSourceRead,
)
from app.domain.motif_knowledge.service import MotifKnowledgeService

router = APIRouter(tags=["motif-knowledge"])


@router.get(
    "/motifs",
    response_model=MotifListResponse,
    status_code=status.HTTP_200_OK,
    summary="List curated motifs"
)
async def list_motifs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    story_status: Optional[MotifStoryStatusEnum] = Query(None),
    narrative_theme: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> MotifListResponse:
    service = MotifKnowledgeService(db)
    return await service.list_motifs(
        limit=limit,
        offset=offset,
        story_status=story_status,
        narrative_theme=narrative_theme
    )


@router.get(
    "/motifs/{motif_id_or_key}",
    response_model=MotifRead,
    status_code=status.HTTP_200_OK,
    summary="Get motif details"
)
async def get_motif(
    motif_id_or_key: str,
    db: AsyncSession = Depends(get_db)
) -> MotifRead:
    service = MotifKnowledgeService(db)
    try:
        return await service.get_motif(motif_id_or_key)
    except MotifNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/motif-story-claims",
    response_model=MotifStoryClaimListResponse,
    status_code=status.HTTP_200_OK,
    summary="List motif story claims"
)
async def list_claims(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    motif_id: Optional[str] = Query(None),
    status_param: Optional[MotifStoryStatusEnum] = Query(None, alias="status"),
    narrative_theme: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> MotifStoryClaimListResponse:
    service = MotifKnowledgeService(db)
    return await service.list_claims(
        limit=limit,
        offset=offset,
        motif_id_or_key=motif_id,
        status=status_param,
        narrative_theme=narrative_theme
    )


@router.get(
    "/motif-story-claims/{claim_id_or_key}",
    response_model=MotifStoryClaimRead,
    status_code=status.HTTP_200_OK,
    summary="Get motif story claim details"
)
async def get_claim(
    claim_id_or_key: str,
    db: AsyncSession = Depends(get_db)
) -> MotifStoryClaimRead:
    service = MotifKnowledgeService(db)
    try:
        return await service.get_claim(claim_id_or_key)
    except ClaimNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/sources/{source_id_or_key}",
    response_model=CuratedSourceRead,
    status_code=status.HTTP_200_OK,
    summary="Get curated source details"
)
async def get_source(
    source_id_or_key: str,
    db: AsyncSession = Depends(get_db)
) -> CuratedSourceRead:
    service = MotifKnowledgeService(db)
    try:
        return await service.get_source(source_id_or_key)
    except SourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
