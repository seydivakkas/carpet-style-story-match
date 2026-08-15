import uuid
from typing import Optional, List, Tuple
from sqlalchemy.exc import IntegrityError
from app.db.models.carpet import CarpetModel
from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.schemas import CarpetCreate, CarpetUpdate
from app.domain.carpets.exceptions import CarpetNotFoundError, CarpetSkuConflictError

class CarpetService:
    def __init__(self, repo: CarpetRepository):
        self.repo = repo

    async def create_carpet(self, carpet_in: CarpetCreate) -> CarpetModel:
        if carpet_in.sku:
            existing = await self.repo.get_by_sku(carpet_in.sku)
            if existing:
                raise CarpetSkuConflictError(carpet_in.sku)

        try:
            return await self.repo.create(carpet_in)
        except IntegrityError as exc:
            await self.repo.session.rollback()
            if carpet_in.sku:
                raise CarpetSkuConflictError(carpet_in.sku) from exc
            raise exc

    async def get_carpet_by_id(self, carpet_id: uuid.UUID) -> CarpetModel:
        carpet = await self.repo.get_by_id(carpet_id)
        if not carpet:
            raise CarpetNotFoundError(carpet_id)
        return carpet

    async def list_carpets(
        self,
        limit: int = 20,
        offset: int = 0,
        manufacturer: Optional[str] = None,
        collection: Optional[str] = None,
        style_label: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[CarpetModel], int]:
        return await self.repo.list(
            limit=limit,
            offset=offset,
            manufacturer=manufacturer,
            collection=collection,
            style_label=style_label,
            is_active=is_active
        )

    async def update_carpet(self, carpet_id: uuid.UUID, update_data: CarpetUpdate) -> CarpetModel:
        carpet = await self.get_carpet_by_id(carpet_id)

        if update_data.sku is not None and update_data.sku != carpet.sku:
            existing = await self.repo.get_by_sku(update_data.sku)
            if existing:
                raise CarpetSkuConflictError(update_data.sku)

        try:
            return await self.repo.update(carpet, update_data)
        except IntegrityError as exc:
            await self.repo.session.rollback()
            if update_data.sku:
                raise CarpetSkuConflictError(update_data.sku) from exc
            raise exc

    async def delete_carpet(self, carpet_id: uuid.UUID) -> None:
        carpet = await self.get_carpet_by_id(carpet_id)
        await self.repo.delete(carpet)
