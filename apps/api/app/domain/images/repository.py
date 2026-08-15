import uuid
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet_image import CarpetImageModel

class CarpetImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        carpet_id: uuid.UUID,
        original_filename: str,
        content_type: str,
        storage_backend: str,
        storage_key: str,
        byte_size: int,
        width_px: int,
        height_px: int,
        channels: int,
        sha256: str,
        is_primary: bool
    ) -> CarpetImageModel:
        image = CarpetImageModel(
            id=uuid.uuid4(),
            carpet_id=carpet_id,
            original_filename=original_filename,
            content_type=content_type,
            storage_backend=storage_backend,
            storage_key=storage_key,
            byte_size=byte_size,
            width_px=width_px,
            height_px=height_px,
            channels=channels,
            sha256=sha256,
            is_primary=is_primary
        )
        self.session.add(image)
        await self.session.commit()
        await self.session.refresh(image)
        return image

    async def get_by_id(self, image_id: uuid.UUID) -> Optional[CarpetImageModel]:
        stmt = select(CarpetImageModel).where(CarpetImageModel.id == image_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sha256(self, carpet_id: uuid.UUID, sha256: str) -> Optional[CarpetImageModel]:
        stmt = select(CarpetImageModel).where(
            CarpetImageModel.carpet_id == carpet_id,
            CarpetImageModel.sha256 == sha256
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_carpet_id(self, carpet_id: uuid.UUID) -> List[CarpetImageModel]:
        stmt = select(CarpetImageModel).where(
            CarpetImageModel.carpet_id == carpet_id
        ).order_by(CarpetImageModel.created_at.asc(), CarpetImageModel.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_carpet_id(self, carpet_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(CarpetImageModel).where(
            CarpetImageModel.carpet_id == carpet_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete(self, image: CarpetImageModel) -> None:
        await self.session.delete(image)
        await self.session.commit()
