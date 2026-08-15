"""Pydantic v2 schemas for Narrative Affinity Engine v1."""
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityStatusEnum,
    NarrativeAffinityLevelEnum,
    NarrativeNotAvailableReasonEnum,
    ThemeSupportStatusEnum
)
from app.db.models.preference_assessment import NarrativeInterestLevelEnum
from app.domain.motif_knowledge.schemas import ClaimSourceRead


class NarrativeAffinityCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carpet_id: uuid.UUID = Field(..., description="Target catalog carpet UUID")


class ThemeEvidenceDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documented_claim_keys: List[str] = Field(default_factory=list)
    contextual_claim_keys: List[str] = Field(default_factory=list)
    contested_claim_keys: List[str] = Field(default_factory=list)
    story_association_ids: List[str] = Field(default_factory=list)


class NarrativeAffinityThemeResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_key: str
    user_interest_level: NarrativeInterestLevelEnum
    user_interest_weight: float
    user_selected: bool
    carpet_support_status: ThemeSupportStatusEnum
    confirmed_match: bool
    contested_overlap: bool
    has_contested_evidence: bool = False
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AlignedThemeExplanationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_key: str
    user_interest_level: NarrativeInterestLevelEnum
    carpet_support_status: ThemeSupportStatusEnum
    context_note: Optional[str] = None
    applicability_note: Optional[str] = None
    summary_tr: str
    sources: List[ClaimSourceRead] = Field(default_factory=list)


class UnmatchedThemeExplanationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_key: str
    user_interest_level: NarrativeInterestLevelEnum
    carpet_support_status: ThemeSupportStatusEnum
    summary_tr: str


class ContestedOverlapExplanationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme_key: str
    user_interest_level: NarrativeInterestLevelEnum
    contest_note: Optional[str] = None
    applicability_note: Optional[str] = None
    summary_tr: str
    sources: List[ClaimSourceRead] = Field(default_factory=list)


class NarrativeAffinityExplanationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_text_tr: str
    aligned_themes: List[AlignedThemeExplanationRead] = Field(default_factory=list)
    unmatched_themes: List[UnmatchedThemeExplanationRead] = Field(default_factory=list)
    contested_overlaps: List[ContestedOverlapExplanationRead] = Field(default_factory=list)


class NarrativeAffinityResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assessment_id: uuid.UUID
    user_narrative_profile_id: uuid.UUID
    carpet_id: uuid.UUID
    affinity_version: str
    carpet_narrative_snapshot_hash: str
    status: NarrativeAffinityStatusEnum
    not_available_reason: Optional[NarrativeNotAvailableReasonEnum] = None
    affinity_level: Optional[NarrativeAffinityLevelEnum] = None
    confirmed_interest_coverage: Optional[float] = None
    selected_theme_count: int
    selected_interest_weight: float
    confirmed_matched_theme_count: int
    confirmed_matched_interest_weight: float
    contested_overlap_count: int
    created_at: datetime
    theme_results: List[NarrativeAffinityThemeResultRead] = Field(default_factory=list)


class NarrativeAffinityDetailRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: NarrativeAffinityResultRead
    explanation: NarrativeAffinityExplanationRead
