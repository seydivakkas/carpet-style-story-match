import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.carpets.exceptions import CarpetNotFoundError
from app.domain.images.exceptions import CarpetImageNotFoundError
from app.domain.styledna.service import StyleDNAService
from app.domain.styledna.schemas import CarpetStyleProfileRead
from app.domain.styledna.exceptions import (
    StyleDNANotFoundError,
    StyleDNAInputUnavailableError,
    StyleDNAAnalysisFailedError
)

router = APIRouter(prefix="/carpets/{carpet_id}/images/{image_id}/style-dna", tags=["Style DNA"])

@router.post(
    "",
    response_model=CarpetStyleProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate & Persist 9D Style DNA Profile for Carpet Image"
)
async def calculate_style_dna(
    carpet_id: uuid.UUID,
    image_id: uuid.UUID,
    response: Response,
    session: AsyncSession = Depends(get_db)
):
    service = StyleDNAService(session)
    try:
        profile, reused = await service.calculate_and_persist_style_dna(carpet_id, image_id)
        if reused:
            response.status_code = status.HTTP_200_OK
        return profile
    except CarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(e)}
        ) from e
    except CarpetImageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_IMAGE_NOT_FOUND", "message": str(e)}
        ) from e
    except StyleDNAInputUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "STYLE_DNA_INPUT_UNAVAILABLE", "message": str(e)}
        ) from e
    except StyleDNAAnalysisFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "STYLE_DNA_ANALYSIS_FAILED", "message": str(e)}
        ) from e

@router.get(
    "",
    response_model=CarpetStyleProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get 9D Style DNA Profile for Carpet Image"
)
async def get_style_dna(
    carpet_id: uuid.UUID,
    image_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
):
    service = StyleDNAService(session)
    try:
        return await service.get_style_dna_profile(carpet_id, image_id)
    except CarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(e)}
        ) from e
    except CarpetImageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_IMAGE_NOT_FOUND", "message": str(e)}
        ) from e
    except StyleDNAInputUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "STYLE_DNA_INPUT_UNAVAILABLE", "message": str(e)}
        ) from e
    except StyleDNANotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STYLE_DNA_NOT_FOUND", "message": str(e)}
        ) from e
