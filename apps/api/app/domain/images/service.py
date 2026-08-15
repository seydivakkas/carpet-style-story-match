import uuid
from typing import List, Tuple
from sqlalchemy.exc import IntegrityError
from app.db.models.carpet_image import CarpetImageModel
from app.domain.carpets.service import CarpetService
from app.domain.images.repository import CarpetImageRepository
from app.domain.images.storage import ImageStorage
from app.domain.images.validation import ImageValidationService
from app.domain.images.exceptions import (
    CarpetImageNotFoundError,
    ImageDuplicateError,
    ImageStorageFailedError
)

class CarpetImageService:
    def __init__(
        self,
        carpet_service: CarpetService,
        image_repo: CarpetImageRepository,
        storage: ImageStorage,
        validator: ImageValidationService
    ):
        self.carpet_service = carpet_service
        self.image_repo = image_repo
        self.storage = storage
        self.validator = validator

    async def upload_carpet_image(
        self,
        carpet_id: uuid.UUID,
        original_filename: str,
        content_type: str,
        file_bytes: bytes
    ) -> CarpetImageModel:
        # 1. Verify Carpet exists (raises CarpetNotFoundError if missing)
        await self.carpet_service.get_carpet_by_id(carpet_id)

        # 2. Validate and process raw image bytes
        (
            canonical_bytes,
            clean_mime,
            extension,
            byte_size,
            width_px,
            height_px,
            channels,
            sha256
        ) = self.validator.validate_and_process_upload(file_bytes, content_type)

        # 3. Check for Duplicate Image for this Carpet
        existing_dup = await self.image_repo.get_by_sha256(carpet_id, sha256)
        if existing_dup:
            raise ImageDuplicateError(carpet_id, sha256)

        # 4. Primary Image Determination
        existing_count = await self.image_repo.count_by_carpet_id(carpet_id)
        is_primary = (existing_count == 0)

        # 5. Atomic Storage Persistence & DB Insertion
        image_id = uuid.uuid4()
        storage_key = self.storage.save_image(carpet_id, image_id, canonical_bytes, extension)

        try:
            image_model = CarpetImageModel(
                id=image_id,
                carpet_id=carpet_id,
                original_filename=original_filename or "unnamed_image",
                content_type=clean_mime,
                storage_backend="LOCAL_FILESYSTEM",
                storage_key=storage_key,
                byte_size=byte_size,
                width_px=width_px,
                height_px=height_px,
                channels=channels,
                sha256=sha256,
                is_primary=is_primary
            )
            self.image_repo.session.add(image_model)
            await self.image_repo.session.commit()
            await self.image_repo.session.refresh(image_model)
            return image_model
        except IntegrityError as exc:
            # DB insert failed -> rollback DB & cleanup orphan file from storage
            await self.image_repo.session.rollback()
            self.storage.delete_image(storage_key)
            if "uq_carpet_image_sha256" in str(exc) or "carpet_images.sha256" in str(exc) or "carpet_id, carpet_images.sha256" in str(exc):
                raise ImageDuplicateError(carpet_id, sha256) from exc
            raise ImageStorageFailedError(f"Database insertion failed: {exc}") from exc
        except Exception as exc:
            await self.image_repo.session.rollback()
            self.storage.delete_image(storage_key)
            raise exc

    async def list_carpet_images(self, carpet_id: uuid.UUID) -> List[CarpetImageModel]:
        # Verify Carpet exists
        await self.carpet_service.get_carpet_by_id(carpet_id)
        return await self.image_repo.list_by_carpet_id(carpet_id)

    async def get_carpet_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID) -> CarpetImageModel:
        # Verify Carpet exists
        await self.carpet_service.get_carpet_by_id(carpet_id)
        image = await self.image_repo.get_by_id(image_id)
        if not image or image.carpet_id != carpet_id:
            raise CarpetImageNotFoundError(image_id)
        return image

    async def get_carpet_image_content(self, carpet_id: uuid.UUID, image_id: uuid.UUID) -> Tuple[bytes, str]:
        image = await self.get_carpet_image(carpet_id, image_id)
        content_bytes = self.storage.get_image_bytes(image.storage_key)
        return content_bytes, image.content_type

    async def delete_carpet_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID) -> None:
        image = await self.get_carpet_image(carpet_id, image_id)
        storage_key = image.storage_key
        
        # Remove DB record first
        await self.image_repo.delete(image)
        
        # Remove stored file on disk
        self.storage.delete_image(storage_key)

    async def delete_all_carpet_images(self, carpet_id: uuid.UUID) -> None:
        images = await self.image_repo.list_by_carpet_id(carpet_id)
        for img in images:
            self.storage.delete_image(img.storage_key)
        self.storage.delete_carpet_dir(carpet_id)
