"""Pydantic schemas for Carpet Catalog + Curated Story Associations v1."""
from datetime import datetime
import enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.carpet import CarpetSourceType
from app.db.models.carpet_story_association import MotifEvidenceTypeEnum
from app.db.models.motif_knowledge import MotifStoryStatusEnum
from app.domain.motif_knowledge.schemas import ClaimSourceRead


from app.domain.common.readiness import StyleDnaReadinessEnum


# --- READ SCHEMAS ---

class PrimaryImageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_id: uuid.UUID
    file_path: str
    width: int
    height: int


class CatalogCarpetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    collection: Optional[str] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    material: Optional[str] = None
    style_label: Optional[str] = None
    source_type: CarpetSourceType
    source_reference: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    primary_image: Optional[PrimaryImageSummary] = None
    style_dna_readiness: Optional[StyleDnaReadinessEnum] = None


class CatalogCarpetListResponse(BaseModel):
    total_count: int
    carpets: List[CatalogCarpetRead]


class CatalogCarpetDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    carpet: CatalogCarpetRead
    primary_image: Optional[PrimaryImageSummary] = None
    style_dna_readiness: StyleDnaReadinessEnum
    motif_association_count: int
    story_association_count: int


class CarpetMotifAssociationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    carpet_id: uuid.UUID
    motif_id: uuid.UUID
    motif_key: str
    motif_name_tr: str
    evidence_type: MotifEvidenceTypeEnum
    curation_note: Optional[str] = None
    uncertainty_note: Optional[str] = None
    presence_sources: List[ClaimSourceRead] = Field(default_factory=list)
    story_association_count: int


class CarpetStoryAssociationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    carpet_motif_association_id: uuid.UUID
    motif_key: str
    motif_name_tr: str
    motif_evidence_type: MotifEvidenceTypeEnum
    claim_id: uuid.UUID
    claim_key: str
    status: MotifStoryStatusEnum
    claim_text_tr: Optional[str] = None
    context_note: Optional[str] = None
    contest_note: Optional[str] = None
    applicability_note: Optional[str] = None
    themes: List[str] = Field(default_factory=list)
    presence_sources: List[ClaimSourceRead] = Field(default_factory=list)
    claim_sources: List[ClaimSourceRead] = Field(default_factory=list)


# --- IMPORT SCHEMAS ---

class CatalogMotifSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    locator: Optional[str] = None
    source_note: Optional[str] = None


class CatalogStoryAssociationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_key: str
    applicability_note: Optional[str] = None


class CatalogMotifAssociationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif_key: str
    evidence_type: MotifEvidenceTypeEnum = MotifEvidenceTypeEnum.CURATOR_CONFIRMED
    curation_note: Optional[str] = None
    uncertainty_note: Optional[str] = None
    sources: List[CatalogMotifSourceInput] = Field(default_factory=list)
    story_claim_keys: List[CatalogStoryAssociationInput] = Field(default_factory=list)


class CatalogCarpetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str
    name: str
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    collection: Optional[str] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    material: Optional[str] = None
    style_label: Optional[str] = None
    source_reference: Optional[str] = None
    is_active: bool = True
    motifs: List[CatalogMotifAssociationInput] = Field(default_factory=list)


class CatalogImportDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="carpet-catalog-curation-v1")
    carpets: List[CatalogCarpetInput] = Field(default_factory=list)
