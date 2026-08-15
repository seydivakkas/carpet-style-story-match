"""Database repository for Historical Connection Engine v1."""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.carpet import CarpetModel
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.db.models.carpet_historical_reference import (
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel
)
from app.db.models.carpet_historical_connection import (
    HistoricalConnectionResultModel,
    HistoricalConnectionDimensionModel
)


class HistoricalConnectionRepository:
    """Database repository for historical connection evaluation persistence and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, connection_id: uuid.UUID) -> Optional[HistoricalConnectionResultModel]:
        stmt = (
            select(HistoricalConnectionResultModel)
            .options(
                selectinload(HistoricalConnectionResultModel.target_carpet),
                selectinload(HistoricalConnectionResultModel.target_style_profile),
                selectinload(HistoricalConnectionResultModel.historical_carpet),
                selectinload(HistoricalConnectionResultModel.historical_reference_metadata),
                selectinload(HistoricalConnectionResultModel.historical_reference_metadata).selectinload(HistoricalReferenceMetadataModel.source_links).selectinload(HistoricalReferenceSourceModel.source),
                selectinload(HistoricalConnectionResultModel.historical_style_profile),
                selectinload(HistoricalConnectionResultModel.dimensions)
            )
            .where(HistoricalConnectionResultModel.id == connection_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        target_style_profile_id: uuid.UUID,
        historical_style_profile_id: uuid.UUID,
        connection_version: str
    ) -> Optional[HistoricalConnectionResultModel]:
        stmt = (
            select(HistoricalConnectionResultModel)
            .options(
                selectinload(HistoricalConnectionResultModel.target_carpet),
                selectinload(HistoricalConnectionResultModel.target_style_profile),
                selectinload(HistoricalConnectionResultModel.historical_carpet),
                selectinload(HistoricalConnectionResultModel.historical_reference_metadata),
                selectinload(HistoricalConnectionResultModel.historical_reference_metadata).selectinload(HistoricalReferenceMetadataModel.source_links).selectinload(HistoricalReferenceSourceModel.source),
                selectinload(HistoricalConnectionResultModel.historical_style_profile),
                selectinload(HistoricalConnectionResultModel.dimensions)
            )
            .where(
                HistoricalConnectionResultModel.target_style_profile_id == target_style_profile_id,
                HistoricalConnectionResultModel.historical_style_profile_id == historical_style_profile_id,
                HistoricalConnectionResultModel.connection_version == connection_version
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_style_profile_by_id(self, profile_id: uuid.UUID) -> Optional[CarpetStyleProfileModel]:
        stmt = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .where(CarpetStyleProfileModel.id == profile_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_carpet_by_id(self, carpet_id: uuid.UUID) -> Optional[CarpetModel]:
        stmt = select(CarpetModel).where(CarpetModel.id == carpet_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_historical_reference(self, identifier: str) -> Optional[HistoricalReferenceMetadataModel]:
        stmt = (
            select(HistoricalReferenceMetadataModel)
            .options(
                selectinload(HistoricalReferenceMetadataModel.carpet),
                selectinload(HistoricalReferenceMetadataModel.source_links).selectinload(HistoricalReferenceSourceModel.source)
            )
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
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .where(
                CarpetStyleProfileModel.carpet_id == carpet_id,
                CarpetStyleProfileModel.algorithm_version == "style-dna-v1.0.0"
            )
            .order_by(CarpetStyleProfileModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_connection_result(
        self,
        result_model: HistoricalConnectionResultModel,
        dimension_models: List[HistoricalConnectionDimensionModel]
    ) -> HistoricalConnectionResultModel:
        self.session.add(result_model)
        await self.session.flush()

        for dim in dimension_models:
            dim.historical_connection_id = result_model.id
            self.session.add(dim)

        await self.session.commit()
        return await self.get_by_id(result_model.id)

    async def list_connection_results(
        self,
        limit: int = 20,
        offset: int = 0,
        target_style_profile_id: Optional[uuid.UUID] = None,
        historical_reference_id: Optional[str] = None
    ) -> Tuple[List[HistoricalConnectionResultModel], int]:
        base_query = select(HistoricalConnectionResultModel)

        if target_style_profile_id:
            base_query = base_query.where(HistoricalConnectionResultModel.target_style_profile_id == target_style_profile_id)

        if historical_reference_id:
            ref = await self.get_historical_reference(historical_reference_id)
            if ref:
                base_query = base_query.where(HistoricalConnectionResultModel.historical_reference_metadata_id == ref.id)
            else:
                return [], 0

        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar_one()

        paginated_stmt = (
            base_query
            .order_by(HistoricalConnectionResultModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(paginated_stmt)
        records = list(res.scalars().all())

        return records, total_count
