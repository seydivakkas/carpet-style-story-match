import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel
from app.domain.carpets.schemas import CarpetCreate, CarpetUpdate

class CarpetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, carpet_in: CarpetCreate) -> CarpetModel:
        carpet = CarpetModel(
            id=uuid.uuid4(),
            sku=carpet_in.sku,
            name=carpet_in.name,
            description=carpet_in.description,
            manufacturer=carpet_in.manufacturer,
            collection=carpet_in.collection,
            width_cm=carpet_in.width_cm,
            height_cm=carpet_in.height_cm,
            material=carpet_in.material,
            style_label=carpet_in.style_label,
            source_type=carpet_in.source_type,
            source_reference=carpet_in.source_reference,
            is_active=carpet_in.is_active
        )
        self.session.add(carpet)
        await self.session.commit()
        await self.session.refresh(carpet)
        return carpet

    async def get_by_id(self, carpet_id: uuid.UUID) -> Optional[CarpetModel]:
        stmt = select(CarpetModel).where(CarpetModel.id == carpet_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Optional[CarpetModel]:
        if not sku:
            return None
        stmt = select(CarpetModel).where(CarpetModel.sku == sku)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        manufacturer: Optional[str] = None,
        collection: Optional[str] = None,
        style_label: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[CarpetModel], int]:
        stmt = select(CarpetModel)
        count_stmt = select(func.count()).select_from(CarpetModel)

        filters = []
        if manufacturer is not None:
            filters.append(CarpetModel.manufacturer == manufacturer)
        if collection is not None:
            filters.append(CarpetModel.collection == collection)
        if style_label is not None:
            filters.append(CarpetModel.style_label == style_label)
        if is_active is not None:
            filters.append(CarpetModel.is_active == is_active)

        if filters:
            for f in filters:
                stmt = stmt.where(f)
                count_stmt = count_stmt.where(f)

        # Deterministic sorting: created_at DESC, id ASC
        stmt = stmt.order_by(CarpetModel.created_at.desc(), CarpetModel.id.asc())
        stmt = stmt.offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar() or 0

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def update(self, carpet: CarpetModel, update_data: CarpetUpdate) -> CarpetModel:
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(carpet, field, value)

        await self.session.commit()
        await self.session.refresh(carpet)
        return carpet

    async def delete(self, carpet: CarpetModel) -> None:
        await self.session.delete(carpet)
        await self.session.commit()
