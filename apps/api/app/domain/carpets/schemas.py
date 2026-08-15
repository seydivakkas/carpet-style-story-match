import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.db.models.carpet import CarpetSourceType

class CarpetBase(BaseModel):
    sku: Optional[str] = Field(None, max_length=100, description="Unique SKU code")
    name: str = Field(..., max_length=255, description="Carpet name")
    description: Optional[str] = Field(None, description="Detailed description")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Manufacturer brand name")
    collection: Optional[str] = Field(None, max_length=255, description="Collection name")
    width_cm: Optional[float] = Field(None, gt=0, description="Width in centimeters (> 0)")
    height_cm: Optional[float] = Field(None, gt=0, description="Height in centimeters (> 0)")
    material: Optional[str] = Field(None, max_length=255, description="Material specification")
    style_label: Optional[str] = Field(None, max_length=100, description="Catalog style label metadata")
    source_type: CarpetSourceType = Field(CarpetSourceType.CATALOG, description="Origin classification")
    source_reference: Optional[str] = Field(None, max_length=255, description="External reference ID")
    is_active: bool = Field(True, description="Active catalog status")

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_trimmed = v.strip()
            return v_trimmed if v_trimmed else None
        return v

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Name must be a string")
        v_trimmed = v.strip()
        if not v_trimmed:
            raise ValueError("Carpet name cannot be empty or whitespace-only")
        return v_trimmed

class CarpetCreate(CarpetBase):
    pass

class CarpetUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=255)
    collection: Optional[str] = Field(None, max_length=255)
    width_cm: Optional[float] = Field(None, gt=0)
    height_cm: Optional[float] = Field(None, gt=0)
    material: Optional[str] = Field(None, max_length=255)
    style_label: Optional[str] = Field(None, max_length=100)
    source_type: Optional[CarpetSourceType] = None
    source_reference: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_trimmed = v.strip()
            return v_trimmed if v_trimmed else None
        return v

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Name must be a string")
        v_trimmed = v.strip()
        if not v_trimmed:
            raise ValueError("Carpet name cannot be empty or whitespace-only")
        return v_trimmed

class CarpetRead(CarpetBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CarpetListResponse(BaseModel):
    items: List[CarpetRead]
    total: int
    limit: int
    offset: int
