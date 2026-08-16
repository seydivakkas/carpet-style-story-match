"""Repository for Carpet Catalog & Story Association queries."""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetMotifAssociationSourceModel,
    CarpetStoryAssociationModel,
)
from app.db.models.motif_knowledge import MotifStoryClaimModel, MotifStoryClaimSourceModel
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION


from app.db.models.manufacturer_brand import ManufacturerBrandModel


class CarpetCatalogRepository:
    """Read-only database repository for catalog carpet queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_brands(self, verified_only: bool = False) -> Tuple[List[ManufacturerBrandModel], int]:
        stmt = select(ManufacturerBrandModel)
        if verified_only:
            stmt = stmt.where(ManufacturerBrandModel.is_verified.is_(True))
        stmt = stmt.order_by(ManufacturerBrandModel.brand_name.asc())
        
        count_stmt = select(func.count(ManufacturerBrandModel.id))
        if verified_only:
            count_stmt = count_stmt.where(ManufacturerBrandModel.is_verified.is_(True))

        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar_one()

        res = await self.session.execute(stmt)
        brands = list(res.scalars().all())
        return brands, total_count

    async def get_brand_by_key(self, brand_key: str) -> Optional[ManufacturerBrandModel]:
        stmt = select(ManufacturerBrandModel).where(
            func.lower(ManufacturerBrandModel.brand_key) == brand_key.lower().strip()
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_catalog_carpets(
        self,
        limit: int = 20,
        offset: int = 0,
        manufacturer: Optional[str] = None,
        brand_key: Optional[str] = None,
        collection: Optional[str] = None,
        material: Optional[str] = None,
        style_label: Optional[str] = None
    ) -> Tuple[List[CarpetModel], int]:
        stmt = select(CarpetModel).options(selectinload(CarpetModel.brand)).where(
            CarpetModel.source_type == CarpetSourceType.CATALOG,
            CarpetModel.is_active.is_(True)
        )

        if brand_key:
            stmt = stmt.join(CarpetModel.brand).where(
                func.lower(ManufacturerBrandModel.brand_key) == brand_key.lower().strip()
            )
        elif manufacturer:
            stmt = stmt.where(CarpetModel.manufacturer == manufacturer)

        if collection:
            stmt = stmt.where(CarpetModel.collection == collection)
        if material:
            stmt = stmt.where(CarpetModel.material == material)
        if style_label:
            stmt = stmt.where(CarpetModel.style_label == style_label)

        # Count total
        count_stmt = select(func.count(CarpetModel.id)).where(
            CarpetModel.source_type == CarpetSourceType.CATALOG,
            CarpetModel.is_active.is_(True)
        )
        if brand_key:
            count_stmt = count_stmt.join(CarpetModel.brand).where(
                func.lower(ManufacturerBrandModel.brand_key) == brand_key.lower().strip()
            )
        elif manufacturer:
            count_stmt = count_stmt.where(CarpetModel.manufacturer == manufacturer)

        if collection:
            count_stmt = count_stmt.where(CarpetModel.collection == collection)
        if material:
            count_stmt = count_stmt.where(CarpetModel.material == material)
        if style_label:
            count_stmt = count_stmt.where(CarpetModel.style_label == style_label)

        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar_one()

        stmt = stmt.order_by(
            CarpetModel.manufacturer.asc().nulls_last(),
            CarpetModel.collection.asc().nulls_last(),
            CarpetModel.sku.asc()
        ).offset(offset).limit(limit)

        res = await self.session.execute(stmt)
        carpets = list(res.scalars().all())

        return carpets, total_count

    async def get_catalog_carpet_by_id_or_sku(self, identifier: str) -> Optional[CarpetModel]:
        is_uuid = self._is_valid_uuid(identifier)
        if is_uuid:
            stmt = select(CarpetModel).options(selectinload(CarpetModel.brand)).where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                or_(CarpetModel.id == uuid.UUID(identifier), CarpetModel.sku == identifier)
            )
        else:
            stmt = select(CarpetModel).options(selectinload(CarpetModel.brand)).where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetModel.sku == identifier
            )

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_primary_image(self, carpet_id: uuid.UUID) -> Optional[CarpetImageModel]:
        stmt = select(CarpetImageModel).where(
            CarpetImageModel.carpet_id == carpet_id,
            CarpetImageModel.is_primary.is_(True)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_current_style_profile(self, carpet_id: uuid.UUID) -> Optional[CarpetStyleProfileModel]:
        stmt = select(CarpetStyleProfileModel).where(
            CarpetStyleProfileModel.carpet_id == carpet_id,
            CarpetStyleProfileModel.algorithm_version == STYLE_DNA_ALGORITHM_VERSION
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_carpet_motif_associations(self, carpet_id: uuid.UUID) -> List[CarpetMotifAssociationModel]:
        stmt = (
            select(CarpetMotifAssociationModel)
            .options(
                selectinload(CarpetMotifAssociationModel.motif),
                selectinload(CarpetMotifAssociationModel.presence_sources).selectinload(CarpetMotifAssociationSourceModel.source),
                selectinload(CarpetMotifAssociationModel.story_associations)
            )
            .where(CarpetMotifAssociationModel.carpet_id == carpet_id)
            .order_by(CarpetMotifAssociationModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_carpet_story_associations(self, carpet_id: uuid.UUID) -> List[CarpetStoryAssociationModel]:
        stmt = (
            select(CarpetStoryAssociationModel)
            .options(
                selectinload(CarpetStoryAssociationModel.motif_association).selectinload(CarpetMotifAssociationModel.motif),
                selectinload(CarpetStoryAssociationModel.motif_association).selectinload(CarpetMotifAssociationModel.presence_sources).selectinload(CarpetMotifAssociationSourceModel.source),
                selectinload(CarpetStoryAssociationModel.claim).selectinload(MotifStoryClaimModel.themes),
                selectinload(CarpetStoryAssociationModel.claim).selectinload(MotifStoryClaimModel.sources).selectinload(MotifStoryClaimSourceModel.source)
            )
            .join(CarpetStoryAssociationModel.motif_association)
            .where(CarpetMotifAssociationModel.carpet_id == carpet_id)
            .order_by(CarpetStoryAssociationModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        try:
            uuid.UUID(val)
            return True
        except ValueError:
            return False
