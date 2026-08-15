import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, computed_field

class CarpetImageRead(BaseModel):
    id: uuid.UUID
    carpet_id: uuid.UUID
    original_filename: str
    content_type: str
    storage_backend: str
    byte_size: int
    width_px: int
    height_px: int
    channels: int
    sha256: str
    is_primary: bool
    created_at: datetime

    @computed_field
    def content_url(self) -> str:
        return f"/api/v1/carpets/{self.carpet_id}/images/{self.id}/content"

    model_config = ConfigDict(from_attributes=True)

class CarpetImageListResponse(BaseModel):
    items: List[CarpetImageRead]
    total: int
