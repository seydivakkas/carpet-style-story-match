"""Pydantic v2 schemas for Historical Connection Engine v1."""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.carpet_historical_connection import (
    HistoricalConnectionStatusEnum,
    HistoricalConnectionNotAvailableReasonEnum,
    HistoricalConnectionLevelEnum
)
from app.domain.historical_reference.schemas import HistoricalReferenceSourceRead
from app.domain.historical_connection.constants import (
    HISTORICAL_CONNECTION_VERSION,
    HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS
)


# --- CREATE SCHEMA ---

class HistoricalConnectionCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_style_profile_id: uuid.UUID = Field(..., description="ID of target carpet CarpetStyleProfile")
    historical_reference_id: str = Field(..., description="UUID or reference_key of historical reference object")


# --- READ SCHEMAS ---

class HistoricalConnectionDimensionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension_key: str
    target_value: Optional[float] = None
    target_status: str
    target_confidence: Optional[float] = None
    reference_value: Optional[float] = None
    reference_status: str
    reference_confidence: Optional[float] = None
    difference: Optional[float] = None
    similarity: Optional[float] = None
    comparable: bool


class HistoricalConnectionClosestDimensionRead(BaseModel):
    dimension_key: str
    similarity: float
    target_value: float
    reference_value: float


class HistoricalConnectionMainDifferenceRead(BaseModel):
    dimension_key: str
    difference: float
    target_value: float
    reference_value: float


class HistoricalConnectionReferenceContextRead(BaseModel):
    reference_id: uuid.UUID
    reference_key: str
    institution_name: str
    object_identifier: str
    accession_number: Optional[str] = None
    object_title: str
    culture: Optional[str] = None
    period: Optional[str] = None
    dynasty_or_tradition: Optional[str] = None
    date_display: Optional[str] = None
    date_start_year: Optional[int] = None
    date_end_year: Optional[int] = None
    geography: Optional[str] = None
    medium: Optional[str] = None
    dimensions_text: Optional[str] = None
    department: Optional[str] = None
    credit_line: Optional[str] = None
    object_url: Optional[str] = None
    source_image_url: Optional[str] = None
    rights_statement: Optional[str] = None
    open_access: Optional[bool] = None


class HistoricalConnectionExplanationRead(BaseModel):
    connection_level_label_tr: Optional[str] = None
    closest_dimensions: List[HistoricalConnectionClosestDimensionRead] = Field(default_factory=list)
    main_differences: List[HistoricalConnectionMainDifferenceRead] = Field(default_factory=list)
    low_confidence_dimensions: List[str] = Field(default_factory=list)
    reference_context: HistoricalConnectionReferenceContextRead
    primary_source: HistoricalReferenceSourceRead
    supporting_sources: List[HistoricalReferenceSourceRead] = Field(default_factory=list)
    disclaimer: str
    coverage_note: Optional[str] = None


class HistoricalConnectionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_carpet_id: uuid.UUID
    target_style_profile_id: uuid.UUID
    historical_carpet_id: uuid.UUID
    historical_reference_metadata_id: uuid.UUID
    historical_style_profile_id: uuid.UUID
    connection_version: str
    status: HistoricalConnectionStatusEnum
    not_available_reason: Optional[HistoricalConnectionNotAvailableReasonEnum] = None
    style_similarity: Optional[float] = None
    connection_level: Optional[HistoricalConnectionLevelEnum] = None
    comparable_dimension_count: int
    dimension_coverage: float
    dimensions: List[HistoricalConnectionDimensionRead] = Field(default_factory=list)
    explanation: HistoricalConnectionExplanationRead
    created_at: datetime


class HistoricalConnectionSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_carpet_id: uuid.UUID
    target_style_profile_id: uuid.UUID
    historical_carpet_id: uuid.UUID
    historical_reference_metadata_id: uuid.UUID
    historical_style_profile_id: uuid.UUID
    connection_version: str
    status: HistoricalConnectionStatusEnum
    not_available_reason: Optional[HistoricalConnectionNotAvailableReasonEnum] = None
    style_similarity: Optional[float] = None
    connection_level: Optional[HistoricalConnectionLevelEnum] = None
    comparable_dimension_count: int
    dimension_coverage: float
    created_at: datetime


class HistoricalConnectionListResponse(BaseModel):
    total_count: int
    connections: List[HistoricalConnectionSummaryRead]


class HistoricalConnectionMetaResponse(BaseModel):
    connection_version: str = HISTORICAL_CONNECTION_VERSION
    min_comparable_dimensions: int = HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS
    statuses: List[str] = Field(default_factory=lambda: [e.value for e in HistoricalConnectionStatusEnum])
    not_available_reasons: List[str] = Field(default_factory=lambda: [e.value for e in HistoricalConnectionNotAvailableReasonEnum])
    connection_levels: List[str] = Field(default_factory=lambda: [e.value for e in HistoricalConnectionLevelEnum])
