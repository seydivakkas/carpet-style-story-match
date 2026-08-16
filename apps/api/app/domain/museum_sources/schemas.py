"""Pydantic schemas for Museum Source Acquisition and Rights Metadata v1."""
from datetime import datetime, timezone
import enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AcquisitionStatusEnum(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_NOT_CARPET = "REJECTED_NOT_CARPET"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    INVALID_RECORD = "INVALID_RECORD"
    DUPLICATE_OBJECT = "DUPLICATE_OBJECT"


class A7ReadinessEnum(str, enum.Enum):
    READY_FOR_HISTORICAL_CURATION = "READY_FOR_HISTORICAL_CURATION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class RightsMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_access: Optional[bool] = None
    public_domain: Optional[bool] = None
    rights_statement: Optional[str] = None
    image_reuse_status: str = Field(default="RIGHTS_REVIEW_REQUIRED")
    rights_source: Optional[str] = None


class MuseumObjectSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    provider_key: str
    institution_name: str
    official_object_id: str
    accession_number: Optional[str] = None
    object_title: str
    object_url: str
    source_type: str = Field(default="MUSEUM_OBJECT")
    object_type: Optional[str] = None
    culture: Optional[str] = None
    period: Optional[str] = None
    dynasty_or_tradition: Optional[str] = None
    date_display: Optional[str] = None
    geography: Optional[str] = None
    medium: Optional[str] = None
    dimensions_text: Optional[str] = None
    department: Optional[str] = None
    credit_line: Optional[str] = None
    rights: RightsMetadata = Field(default_factory=RightsMetadata)
    primary_image_source_url: Optional[str] = None
    iiif_manifest_url: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_record_hash: str
    acquisition_status: AcquisitionStatusEnum = AcquisitionStatusEnum.ACCEPTED
    a7_readiness: A7ReadinessEnum = A7ReadinessEnum.READY_FOR_HISTORICAL_CURATION
    rejection_reason: Optional[str] = None


class RegistryProviderEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_key: str
    institution_name: str
    official_base_url: str
    api_reference_url: str
    adapter_class: str
    access_mode: str = Field(default="OPEN_API")
    metadata_usage_note: str
    image_usage_note: str
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = True


class MuseumSourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="museum-source-registry-v1")
    providers: List[RegistryProviderEntry] = Field(default_factory=list)
