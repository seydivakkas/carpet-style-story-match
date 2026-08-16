"""API endpoints for Carpet Catalog & Curated Story Associations (Read-Only)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.carpet_catalog.exceptions import CatalogCarpetNotFoundError
from app.domain.carpet_catalog.schemas import (
    CatalogCarpetListResponse,
    CatalogCarpetDetailRead,
    CarpetMotifAssociationRead,
    CarpetStoryAssociationRead,
    CatalogFacetsResponse,
)
from app.domain.carpet_catalog.service import CarpetCatalogService

router = APIRouter(prefix="/catalog", tags=["carpet-catalog"])


@router.get(
    "/facets",
    response_model=CatalogFacetsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated catalog filter facets"
)
async def get_catalog_facets(
    db: AsyncSession = Depends(get_db)
) -> CatalogFacetsResponse:
    service = CarpetCatalogService(db)
    return await service.get_catalog_facets()


@router.get(
    "/carpets",
    response_model=CatalogCarpetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List catalog carpets"
)
async def list_catalog_carpets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    manufacturer: Optional[str] = Query(None),
    brand_key: Optional[str] = Query(None),
    collection: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    style_label: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> CatalogCarpetListResponse:
    service = CarpetCatalogService(db)
    return await service.list_catalog_carpets(
        limit=limit,
        offset=offset,
        manufacturer=manufacturer,
        brand_key=brand_key,
        collection=collection,
        material=material,
        style_label=style_label
    )


@router.get(
    "/carpets/{carpet_id_or_sku}",
    response_model=CatalogCarpetDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get catalog carpet details"
)
async def get_catalog_carpet(
    carpet_id_or_sku: str,
    db: AsyncSession = Depends(get_db)
) -> CatalogCarpetDetailRead:
    service = CarpetCatalogService(db)
    try:
        return await service.get_catalog_carpet_detail(carpet_id_or_sku)
    except CatalogCarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/carpets/{carpet_id_or_sku}/motifs",
    response_model=List[CarpetMotifAssociationRead],
    status_code=status.HTTP_200_OK,
    summary="List motif associations for a catalog carpet"
)
async def list_carpet_motifs(
    carpet_id_or_sku: str,
    db: AsyncSession = Depends(get_db)
) -> List[CarpetMotifAssociationRead]:
    service = CarpetCatalogService(db)
    try:
        return await service.list_carpet_motifs(carpet_id_or_sku)
    except CatalogCarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/carpets/{carpet_id_or_sku}/story-associations",
    response_model=List[CarpetStoryAssociationRead],
    status_code=status.HTTP_200_OK,
    summary="List story claim associations for a catalog carpet"
)
async def list_carpet_story_associations(
    carpet_id_or_sku: str,
    db: AsyncSession = Depends(get_db)
) -> List[CarpetStoryAssociationRead]:
    service = CarpetCatalogService(db)
    try:
        return await service.list_carpet_story_associations(carpet_id_or_sku)
    except CatalogCarpetNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
