import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.carpets.schemas import (
    CarpetCreate,
    CarpetUpdate,
    CarpetRead,
    CarpetListResponse
)
from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.service import CarpetService
from app.domain.carpets.exceptions import CarpetNotFoundError, CarpetSkuConflictError

router = APIRouter(prefix="/carpets", tags=["carpets"])

def get_carpet_service(db: AsyncSession = Depends(get_db)) -> CarpetService:
    repo = CarpetRepository(db)
    return CarpetService(repo)

@router.post(
    "",
    response_model=CarpetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new carpet record"
)
async def create_carpet(
    carpet_in: CarpetCreate,
    service: CarpetService = Depends(get_carpet_service)
):
    try:
        carpet = await service.create_carpet(carpet_in)
        return carpet
    except CarpetSkuConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CARPET_SKU_CONFLICT",
                "message": str(exc)
            }
        )

@router.get(
    "",
    response_model=CarpetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List carpet records with pagination and filtering"
)
async def list_carpets(
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Offset cursor"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    collection: Optional[str] = Query(None, description="Filter by collection"),
    style_label: Optional[str] = Query(None, description="Filter by catalog style label"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: CarpetService = Depends(get_carpet_service)
):
    items, total = await service.list_carpets(
        limit=limit,
        offset=offset,
        manufacturer=manufacturer,
        collection=collection,
        style_label=style_label,
        is_active=is_active
    )
    return CarpetListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get(
    "/{carpet_id}",
    response_model=CarpetRead,
    status_code=status.HTTP_200_OK,
    summary="Get carpet detail by UUID"
)
async def get_carpet(
    carpet_id: uuid.UUID,
    service: CarpetService = Depends(get_carpet_service)
):
    try:
        carpet = await service.get_carpet_by_id(carpet_id)
        return carpet
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CARPET_NOT_FOUND",
                "message": str(exc)
            }
        )

@router.patch(
    "/{carpet_id}",
    response_model=CarpetRead,
    status_code=status.HTTP_200_OK,
    summary="Update carpet record partially"
)
async def update_carpet(
    carpet_id: uuid.UUID,
    update_data: CarpetUpdate,
    service: CarpetService = Depends(get_carpet_service)
):
    try:
        carpet = await service.update_carpet(carpet_id, update_data)
        return carpet
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CARPET_NOT_FOUND",
                "message": str(exc)
            }
        )
    except CarpetSkuConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CARPET_SKU_CONFLICT",
                "message": str(exc)
            }
        )

@router.delete(
    "/{carpet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a carpet record"
)
async def delete_carpet(
    carpet_id: uuid.UUID,
    service: CarpetService = Depends(get_carpet_service)
):
    try:
        await service.delete_carpet(carpet_id)
        return None
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CARPET_NOT_FOUND",
                "message": str(exc)
            }
        )
