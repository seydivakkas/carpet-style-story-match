"""Pydantic v2 schemas for Historical Reference Collection v1."""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.carpet_historical_reference import HistoricalSourceRoleEnum
from app.domain.common.readiness import StyleDnaReadinessEnum
from app.domain.carpet_catalog.schemas import PrimaryImageSummary
from app.domain.historical_reference.constants import (
    HISTORICAL_REFERENCE_SCHEMA_VERSION,
    HISTORICAL_REFERENCE_API_VERSION
)


# --- IMPORT SCHEMAS ---

class HistoricalSupportingSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(..., description="Key of an existing CuratedSource record")
    locator: Optional[str] = Field(None, description="Page number, catalog entry or locator note")
    source_note: Optional[str] = Field(None, description="Context note for supporting reference link")


class HistoricalReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_key: str = Field(..., description="Stable, unique human-readable reference key")
    primary_source_key: str = Field(..., description="Key of the primary object/archive CuratedSource record")
    supporting_sources: List[HistoricalSupportingSourceInput] = Field(default_factory=list)

    institution_name: str = Field(..., description="Name of holding museum or archive")
    object_identifier: str = Field(..., description="Museum object ID, accession number or stable identifier")
    accession_number: Optional[str] = None
    object_title: str = Field(..., description="Source-reported object title")

    culture: Optional[str] = Field(None, description="Source-reported culture")
    period: Optional[str] = Field(None, description="Source-reported period")
    dynasty_or_tradition: Optional[str] = Field(None, description="Source-reported dynasty or tradition")

    date_display: Optional[str] = Field(None, description="Source-reported textual date")
    date_start_year: Optional[int] = Field(None, description="Explicit normalized start year")
    date_end_year: Optional[int] = Field(None, description="Explicit normalized end year")

    geography: Optional[str] = None
    medium: Optional[str] = None
    dimensions_text: Optional[str] = None

    department: Optional[str] = None
    credit_line: Optional[str] = None

    object_url: Optional[str] = Field(None, description="URL of institutional object webpage")
    source_image_url: Optional[str] = Field(None, description="Metadata URL of reference image")

    rights_statement: Optional[str] = None
    open_access: Optional[bool] = None

    curation_note: Optional[str] = None


class HistoricalReferenceImportDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=HISTORICAL_REFERENCE_SCHEMA_VERSION)
    references: List[HistoricalReferenceInput] = Field(default_factory=list)


# --- READ SCHEMAS ---

class HistoricalReferenceSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    source_role: HistoricalSourceRoleEnum
    source_key: str
    title: str
    citation_text: str
    source_type: str
    locator: Optional[str] = None
    source_note: Optional[str] = None


class HistoricalReferenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    carpet_id: uuid.UUID
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
    department: Optional[str] = None
    source_image_url: Optional[str] = None
    created_at: datetime


class HistoricalReferenceDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    carpet_id: uuid.UUID
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
    curation_note: Optional[str] = None
    schema_version: str
    primary_source: HistoricalReferenceSourceRead
    supporting_sources: List[HistoricalReferenceSourceRead] = Field(default_factory=list)
    primary_image: Optional[PrimaryImageSummary] = None
    style_dna_readiness: StyleDnaReadinessEnum
    created_at: datetime
    updated_at: datetime


class HistoricalReferenceListResponse(BaseModel):
    total_count: int
    references: List[HistoricalReferenceSummary]


class HistoricalReferenceMetaResponse(BaseModel):
    api_version: str = HISTORICAL_REFERENCE_API_VERSION
    curation_schema_version: str = HISTORICAL_REFERENCE_SCHEMA_VERSION
    source_roles: List[str] = Field(default_factory=lambda: [e.value for e in HistoricalSourceRoleEnum])
    style_dna_readiness_states: List[str] = Field(default_factory=lambda: [e.value for e in StyleDnaReadinessEnum])
