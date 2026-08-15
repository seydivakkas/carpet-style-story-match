"""Database repository for Historical Reference Collection v1."""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.db.models.motif_knowledge import CuratedSourceModel
from app.db.models.carpet_historical_reference import (
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel
)


class HistoricalReferenceRepository:
    """Database repository for historical reference queries and curation persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_historical_references(
        self,
        limit: int = 20,
        offset: int = 0,
        institution: Optional[str] = None,
        culture: Optional[str] = None,
        period: Optional[str] = None,
        dynasty_or_tradition: Optional[str] = None,
        department: Optional[str] = None
    ) -> Tuple[List[HistoricalReferenceMetadataModel], int]:
        base_query = (
            select(HistoricalReferenceMetadataModel)
            .join(HistoricalReferenceMetadataModel.carpet)
            .where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
        )

        if institution:
            base_query = base_query.where(HistoricalReferenceMetadataModel.institution_name == institution)
        if culture:
            base_query = base_query.where(HistoricalReferenceMetadataModel.culture == culture)
        if period:
            base_query = base_query.where(HistoricalReferenceMetadataModel.period == period)
        if dynasty_or_tradition:
            base_query = base_query.where(HistoricalReferenceMetadataModel.dynasty_or_tradition == dynasty_or_tradition)
        if department:
            base_query = base_query.where(HistoricalReferenceMetadataModel.department == department)

        # Count total matching records
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar_one()

        # Execute paginated query with stable deterministic ordering
        paginated_stmt = (
            base_query
            .order_by(
                HistoricalReferenceMetadataModel.institution_name.asc(),
                HistoricalReferenceMetadataModel.object_identifier.asc(),
                HistoricalReferenceMetadataModel.reference_key.asc()
            )
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(paginated_stmt)
        records = list(res.scalars().all())

        return records, total_count

    async def get_historical_reference_by_id_or_key(self, identifier: str) -> Optional[HistoricalReferenceMetadataModel]:
        stmt = (
            select(HistoricalReferenceMetadataModel)
            .options(
                selectinload(HistoricalReferenceMetadataModel.carpet),
                selectinload(HistoricalReferenceMetadataModel.source_links).selectinload(HistoricalReferenceSourceModel.source)
            )
            .join(HistoricalReferenceMetadataModel.carpet)
            .where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
        )

        try:
            val_uuid = uuid.UUID(identifier)
            stmt = stmt.where(
                or_(
                    HistoricalReferenceMetadataModel.id == val_uuid,
                    HistoricalReferenceMetadataModel.carpet_id == val_uuid,
                    HistoricalReferenceMetadataModel.reference_key == identifier
                )
            )
        except ValueError:
            stmt = stmt.where(HistoricalReferenceMetadataModel.reference_key == identifier)

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_primary_image(self, carpet_id: uuid.UUID) -> Optional[CarpetImageModel]:
        stmt = (
            select(CarpetImageModel)
            .where(
                CarpetImageModel.carpet_id == carpet_id,
                CarpetImageModel.is_primary == True
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_current_style_profile(self, carpet_id: uuid.UUID) -> Optional[CarpetStyleProfileModel]:
        stmt = (
            select(CarpetStyleProfileModel)
            .where(
                CarpetStyleProfileModel.carpet_id == carpet_id,
                CarpetStyleProfileModel.algorithm_version == "style-dna-v1.0.0"
            )
            .order_by(CarpetStyleProfileModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_curated_source_by_key(self, source_key: str) -> Optional[CuratedSourceModel]:
        stmt = select(CuratedSourceModel).where(CuratedSourceModel.source_key == source_key)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_reference_key(self, reference_key: str) -> Optional[HistoricalReferenceMetadataModel]:
        stmt = (
            select(HistoricalReferenceMetadataModel)
            .options(
                selectinload(HistoricalReferenceMetadataModel.source_links).selectinload(HistoricalReferenceSourceModel.source)
            )
            .where(HistoricalReferenceMetadataModel.reference_key == reference_key)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_institution_and_object_id(
        self,
        institution_name: str,
        object_identifier: str
    ) -> Optional[HistoricalReferenceMetadataModel]:
        stmt = (
            select(HistoricalReferenceMetadataModel)
            .where(
                HistoricalReferenceMetadataModel.institution_name == institution_name,
                HistoricalReferenceMetadataModel.object_identifier == object_identifier
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_historical_reference(
        self,
        carpet_model: CarpetModel,
        metadata_model: HistoricalReferenceMetadataModel,
        source_link_models: List[HistoricalReferenceSourceModel]
    ) -> HistoricalReferenceMetadataModel:
        self.session.add(carpet_model)
        await self.session.flush()

        metadata_model.carpet_id = carpet_model.id
        self.session.add(metadata_model)
        await self.session.flush()

        for sl in source_link_models:
            sl.historical_reference_id = metadata_model.id
            self.session.add(sl)

        return metadata_model
