"""Pydantic schemas for Curated Motif Story + Source Provenance v1."""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.motif_knowledge import SourceTypeEnum, MotifStoryStatusEnum


# --- READ SCHEMAS ---

class CuratedSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_key: str
    source_type: SourceTypeEnum
    title: str
    citation_text: str
    creator_or_institution: Optional[str] = None
    publication_year: Optional[int] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    isbn: Optional[str] = None
    rights_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClaimSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: CuratedSourceRead
    locator: Optional[str] = None
    source_note: Optional[str] = None


class MotifStoryClaimSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_key: str
    status: MotifStoryStatusEnum
    claim_text_tr: Optional[str] = None
    claim_text_en: Optional[str] = None
    context_note: Optional[str] = None
    contest_note: Optional[str] = None
    uncertainty_note: Optional[str] = None
    themes: List[str] = Field(default_factory=list)


class MotifRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    motif_key: str
    name_tr: str
    name_en: Optional[str] = None
    visual_description_tr: Optional[str] = None
    visual_description_en: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    story_claims: List[MotifStoryClaimSummaryRead] = Field(default_factory=list)


class MotifListResponse(BaseModel):
    total_count: int
    motifs: List[MotifRead]


class MotifStoryClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_key: str
    motif_id: uuid.UUID
    motif_key: str
    status: MotifStoryStatusEnum
    claim_text_tr: Optional[str] = None
    claim_text_en: Optional[str] = None
    context_note: Optional[str] = None
    contest_note: Optional[str] = None
    uncertainty_note: Optional[str] = None
    knowledge_version: str
    created_at: datetime
    updated_at: datetime
    themes: List[str] = Field(default_factory=list)
    sources: List[ClaimSourceRead] = Field(default_factory=list)


class MotifStoryClaimListResponse(BaseModel):
    total_count: int
    claims: List[MotifStoryClaimRead]


# --- IMPORT SCHEMAS ---

class SourceImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    source_type: SourceTypeEnum = SourceTypeEnum.OTHER
    title: str
    citation_text: str
    creator_or_institution: Optional[str] = None
    publication_year: Optional[int] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    isbn: Optional[str] = None
    rights_note: Optional[str] = None


class MotifImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif_key: str
    name_tr: str
    name_en: Optional[str] = None
    visual_description_tr: Optional[str] = None
    visual_description_en: Optional[str] = None


class ClaimSourceLinkImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    locator: Optional[str] = None
    source_note: Optional[str] = None


class ClaimImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_key: str
    motif_key: str
    status: MotifStoryStatusEnum
    claim_text_tr: Optional[str] = None
    claim_text_en: Optional[str] = None
    context_note: Optional[str] = None
    contest_note: Optional[str] = None
    uncertainty_note: Optional[str] = None
    source_links: List[ClaimSourceLinkImportItem] = Field(default_factory=list)
    theme_keys: List[str] = Field(default_factory=list)


class CurationImportSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="motif-story-curation-v1")
    sources: List[SourceImportItem] = Field(default_factory=list)
    motifs: List[MotifImportItem] = Field(default_factory=list)
    claims: List[ClaimImportItem] = Field(default_factory=list)
