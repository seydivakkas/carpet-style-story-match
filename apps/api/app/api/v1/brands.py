"""API endpoints for Manufacturer Brands Registry."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.carpet_catalog.exceptions import CatalogCarpetNotFoundError
from app.domain.carpet_catalog.schemas import BrandRead, BrandListResponse
from app.domain.carpet_catalog.service import CarpetCatalogService

router = APIRouter(prefix="/brands", tags=["manufacturer-brands"])


@router.get(
    "",
    response_model=BrandListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verified manufacturer brands"
)
async def list_brands(
    verified_only: bool = Query(False, description="Filter for verified brands only"),
    db: AsyncSession = Depends(get_db)
) -> BrandListResponse:
    service = CarpetCatalogService(db)
    return await service.list_brands(verified_only=verified_only)


@router.get(
    "/{brand_key}",
    response_model=BrandRead,
    status_code=status.HTTP_200_OK,
    summary="Get manufacturer brand details"
)
async def get_brand_detail(
    brand_key: str,
    db: AsyncSession = Depends(get_db)
) -> BrandRead:
    service = CarpetCatalogService(db)
    try:
        return await service.get_brand_detail(brand_key)
    except CatalogCarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
