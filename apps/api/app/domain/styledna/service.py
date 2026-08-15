import uuid
import hashlib
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.exceptions import CarpetNotFoundError
from app.domain.images.repository import CarpetImageRepository
from app.domain.images.storage import LocalImageStorage
from app.domain.images.exceptions import CarpetImageNotFoundError
from app.domain.styledna.repository import StyleDNARepository
from app.domain.styledna.engine import StyleDNAEngine, STYLE_DNA_ALGORITHM_VERSION
from app.domain.styledna.exceptions import (
    StyleDNANotFoundError,
    StyleDNAInputUnavailableError,
    StyleDNAAnalysisFailedError
)
from app.db.models.carpet_style_profile import CarpetStyleProfileModel

class StyleDNAService:
    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[LocalImageStorage] = None
    ):
        self.session = session
        self.carpet_repo = CarpetRepository(session)
        self.image_repo = CarpetImageRepository(session)
        self.style_dna_repo = StyleDNARepository(session)
        self.storage = storage or LocalImageStorage()
        self.engine = StyleDNAEngine()

    async def calculate_and_persist_style_dna(
        self,
        carpet_id: uuid.UUID,
        image_id: uuid.UUID
    ) -> Tuple[CarpetStyleProfileModel, bool]:
        # 1. Verify carpet exists
        carpet = await self.carpet_repo.get_by_id(carpet_id)
        if not carpet:
            raise CarpetNotFoundError(carpet_id)

        # 2. Verify image exists
        image = await self.image_repo.get_by_id(image_id)
        if not image:
            raise CarpetImageNotFoundError(image_id)

        # 3. Verify image belongs to carpet
        if str(image.carpet_id) != str(carpet_id):
            raise StyleDNAInputUnavailableError(
                f"Image ID '{image_id}' does not belong to carpet ID '{carpet_id}'."
            )

        # 4. Check for existing profile (Idempotency)
        existing_profile = await self.style_dna_repo.get_profile_by_image_and_version(
            image_id,
            algorithm_version=STYLE_DNA_ALGORITHM_VERSION
        )
        if existing_profile:
            return existing_profile, True

        # 5. Read image bytes from storage
        try:
            raw_bytes = self.storage.get_image_bytes(image.storage_key)
        except Exception as e:
            raise StyleDNAInputUnavailableError(f"Could not read image file from storage: {e}") from e

        # 6. Calculate analysis_input_sha256
        input_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # 7. Run computer vision analysis engine
        profile_status, dimensions = self.engine.analyze(raw_bytes)

        # 8. Persist profile and dimensions
        profile = await self.style_dna_repo.create_profile(
            carpet_id=carpet_id,
            image_id=image_id,
            algorithm_version=STYLE_DNA_ALGORITHM_VERSION,
            analysis_input_sha256=input_sha256,
            analysis_scope="FULL_IMAGE",
            status=profile_status,
            analyzed_width_px=image.width_px,
            analyzed_height_px=image.height_px,
            dimensions=dimensions
        )

        return profile, False

    async def get_style_dna_profile(
        self,
        carpet_id: uuid.UUID,
        image_id: uuid.UUID
    ) -> CarpetStyleProfileModel:
        # Verify carpet & image
        carpet = await self.carpet_repo.get_by_id(carpet_id)
        if not carpet:
            raise CarpetNotFoundError(carpet_id)

        image = await self.image_repo.get_by_id(image_id)
        if not image:
            raise CarpetImageNotFoundError(image_id)

        if str(image.carpet_id) != str(carpet_id):
            raise StyleDNAInputUnavailableError(
                f"Image ID '{image_id}' does not belong to carpet ID '{carpet_id}'."
            )

        profile = await self.style_dna_repo.get_profile_by_image_and_version(
            image_id,
            algorithm_version=STYLE_DNA_ALGORITHM_VERSION
        )
        if not profile:
            raise StyleDNANotFoundError(image_id)

        return profile
