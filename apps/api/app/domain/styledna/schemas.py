import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator
from app.db.models.carpet_style_profile import StyleProfileStatus, StyleDimensionStatus
from app.domain.contracts import CANONICAL_STYLE_DNA

CANONICAL_KEYS = [d["key"] for d in CANONICAL_STYLE_DNA]

class StyleDimensionRead(BaseModel):
    key: str
    value: Optional[float]
    confidence: float
    status: StyleDimensionStatus
    evidence: Dict[str, Any]
    method_version: str

    model_config = ConfigDict(from_attributes=True)

class CarpetStyleProfileRead(BaseModel):
    id: uuid.UUID
    carpet_id: uuid.UUID
    image_id: uuid.UUID
    algorithm_version: str
    analysis_input_sha256: str
    analysis_scope: str
    status: StyleProfileStatus
    analyzed_width_px: int
    analyzed_height_px: int
    created_at: datetime
    dimensions: List[StyleDimensionRead]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[StyleDimensionRead]) -> List[StyleDimensionRead]:
        dim_map = {d.key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)
