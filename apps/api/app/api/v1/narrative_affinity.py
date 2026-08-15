"""API endpoints for Explainable Narrative Affinity Engine v1."""
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.narrative_affinity.exceptions import (
    NarrativeProfileNotFoundError,
    NarrativeAffinityCarpetNotFoundError,
    NarrativeAffinityRequiresCatalogCarpetError,
    NarrativeAffinityNotFoundError
)
from app.domain.narrative_affinity.schemas import (
    NarrativeAffinityCreateRequest,
    NarrativeAffinityResultRead,
    NarrativeAffinityDetailRead
)
from app.domain.narrative_affinity.service import NarrativeAffinityService

router = APIRouter(
    prefix="/preference-assessments/{assessment_id}/narrative-affinities",
    tags=["narrative-affinity"]
)


@router.post(
    "",
    response_model=NarrativeAffinityDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate narrative affinity between user narrative profile and a catalog carpet"
)
async def calculate_narrative_affinity(
    assessment_id: uuid.UUID,
    body: NarrativeAffinityCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> NarrativeAffinityDetailRead:
    service = NarrativeAffinityService(db)
    try:
        return await service.calculate_narrative_affinity(assessment_id, body.carpet_id)
    except NarrativeProfileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NARRATIVE_AFFINITY_USER_PROFILE_NOT_FOUND", "message": str(e)}
        )
    except NarrativeAffinityCarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NARRATIVE_AFFINITY_CARPET_NOT_FOUND", "message": str(e)}
        )
    except NarrativeAffinityRequiresCatalogCarpetError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NARRATIVE_AFFINITY_REQUIRES_CATALOG_CARPET", "message": str(e)}
        )


@router.get(
    "/{affinity_id}",
    response_model=NarrativeAffinityDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get narrative affinity result details"
)
async def get_narrative_affinity_detail(
    assessment_id: uuid.UUID,
    affinity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> NarrativeAffinityDetailRead:
    service = NarrativeAffinityService(db)
    try:
        return await service.get_narrative_affinity_detail(assessment_id, affinity_id)
    except NarrativeAffinityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NARRATIVE_AFFINITY_NOT_FOUND", "message": str(e)}
        )


@router.get(
    "",
    response_model=List[NarrativeAffinityResultRead],
    status_code=status.HTTP_200_OK,
    summary="List previously computed narrative affinity results for assessment"
)
async def list_narrative_affinities(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[NarrativeAffinityResultRead]:
    service = NarrativeAffinityService(db)
    return await service.list_narrative_affinities(assessment_id)
