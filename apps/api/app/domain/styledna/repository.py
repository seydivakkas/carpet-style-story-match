import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel
)

class StyleDNARepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile_by_image_and_version(
        self,
        image_id: uuid.UUID,
        algorithm_version: str = "style-dna-v1.0.0"
    ) -> Optional[CarpetStyleProfileModel]:
        stmt = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .where(
                CarpetStyleProfileModel.image_id == image_id,
                CarpetStyleProfileModel.algorithm_version == algorithm_version
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_profile_by_id(self, profile_id: uuid.UUID) -> Optional[CarpetStyleProfileModel]:
        stmt = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .where(CarpetStyleProfileModel.id == profile_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_profile(
        self,
        carpet_id: uuid.UUID,
        image_id: uuid.UUID,
        algorithm_version: str,
        analysis_input_sha256: str,
        analysis_scope: str,
        status: Any,
        analyzed_width_px: int,
        analyzed_height_px: int,
        dimensions: List[Dict[str, Any]]
    ) -> CarpetStyleProfileModel:
        profile = CarpetStyleProfileModel(
            carpet_id=carpet_id,
            image_id=image_id,
            algorithm_version=algorithm_version,
            analysis_input_sha256=analysis_input_sha256,
            analysis_scope=analysis_scope,
            status=status,
            analyzed_width_px=analyzed_width_px,
            analyzed_height_px=analyzed_height_px
        )
        self.session.add(profile)
        await self.session.flush()

        for d in dimensions:
            dim = CarpetStyleDimensionModel(
                profile_id=profile.id,
                dimension_key=d["key"],
                value=d["value"],
                confidence=d["confidence"],
                status=d["status"],
                evidence=d["evidence"],
                method_version=d.get("method_version", "v1")
            )
            self.session.add(dim)

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile
