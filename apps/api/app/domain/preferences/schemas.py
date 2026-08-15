import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.db.models.preference_assessment import (
    AssessmentStatus,
    PreferenceDimensionStatus,
    TextChoiceEnum,
    VisualChoiceEnum,
    UserProfileStatusEnum,
    UserPreferenceProvenanceEnum,
    ConfidenceStatusEnum,
    ImportanceLevelEnum,
    ImportanceCompletionModeEnum
)
from app.domain.contracts import CANONICAL_STYLE_DNA

CANONICAL_KEYS = [d["key"] for d in CANONICAL_STYLE_DNA]

class TextQuestionRead(BaseModel):
    question_key: str
    order: int
    prompt_tr: str
    option_a_tr: str
    option_b_tr: str
    primary_dimension: str
    response_scale: List[str]

    model_config = ConfigDict(from_attributes=True)

class TextQuestionsListResponse(BaseModel):
    total_questions: int
    questions: List[TextQuestionRead]

class TextResponseCreate(BaseModel):
    choice: TextChoiceEnum

class TextResponseRead(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    question_key: str
    choice: TextChoiceEnum
    response_value: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TextDimensionRead(BaseModel):
    key: str
    value: Optional[float]
    status: PreferenceDimensionStatus
    evidence_weight: float
    evidence_count: int

    model_config = ConfigDict(from_attributes=True)

class TextPreferenceProfileRead(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    evidence_version: str
    created_at: datetime
    updated_at: datetime
    dimensions: List[TextDimensionRead]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[TextDimensionRead]) -> List[TextDimensionRead]:
        dim_map = {d.key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)

class PreferenceAssessmentRead(BaseModel):
    id: uuid.UUID
    status: AssessmentStatus
    evidence_version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# VISUAL PREFERENCE SCHEMAS (GÖREV 05)
# ---------------------------------------------------------

class VisualStimulusRead(BaseModel):
    stimulus_key: str
    target_dimension: str
    base_family: str
    description: str

class VisualStimuliListResponse(BaseModel):
    total_stimuli: int
    stimuli: List[VisualStimulusRead]

class VisualPresentationRead(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    stimulus_key: str
    left_asset_url: str
    right_asset_url: str

    model_config = ConfigDict(from_attributes=True)

class VisualResponseCreate(BaseModel):
    choice: VisualChoiceEnum

class VisualResponseRead(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    stimulus_key: str
    choice: VisualChoiceEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VisualDimensionRead(BaseModel):
    key: str
    value: Optional[float]
    status: PreferenceDimensionStatus
    evidence_weight: float
    evidence_count: int

    model_config = ConfigDict(from_attributes=True)

class VisualPreferenceProfileRead(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    evidence_version: str
    stimulus_version: str
    created_at: datetime
    updated_at: datetime
    dimensions: List[VisualDimensionRead]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[VisualDimensionRead]) -> List[VisualDimensionRead]:
        dim_map = {d.key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# MULTIMODAL PREFERENCE SCHEMAS (GÖREV 06)
# ---------------------------------------------------------

class DimensionOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float = Field(..., ge=0.0, le=1.0)

class UserPreferenceDimensionResponse(BaseModel):
    dimension_key: str
    inferred_value: Optional[float]
    final_value: Optional[float]
    status: PreferenceDimensionStatus
    provenance: UserPreferenceProvenanceEnum
    text_value: Optional[float]
    text_evidence_weight: float
    visual_value: Optional[float]
    visual_evidence_weight: float

    @property
    def key(self) -> str:
        return self.dimension_key

    model_config = ConfigDict(from_attributes=True)

class UserPreferenceProfileResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    profile_version: str
    status: UserProfileStatusEnum
    created_at: datetime
    updated_at: datetime
    dimensions: List[UserPreferenceDimensionResponse]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[UserPreferenceDimensionResponse]) -> List[UserPreferenceDimensionResponse]:
        dim_map = {d.dimension_key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)

class PreferenceConfidenceDimensionResponse(BaseModel):
    dimension_key: str
    confidence: Optional[float]
    status: ConfidenceStatusEnum
    modality_count: int
    agreement: Optional[float]
    source_coverage: float
    evidence_json: Optional[str] = None

    @property
    def key(self) -> str:
        return self.dimension_key

    model_config = ConfigDict(from_attributes=True)

class PreferenceConfidenceProfileResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    preference_profile_id: uuid.UUID
    confidence_version: str
    created_at: datetime
    updated_at: datetime
    dimensions: List[PreferenceConfidenceDimensionResponse]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[PreferenceConfidenceDimensionResponse]) -> List[PreferenceConfidenceDimensionResponse]:
        dim_map = {d.dimension_key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# IMPORTANCE PROFILE SCHEMAS (GÖREV 07)
# ---------------------------------------------------------

class ImportanceSelectionRequest(BaseModel):
    skip: bool = False
    priority_dimensions: List[str] = Field(default_factory=list)
    flexible_dimensions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

class ImportanceDimensionResponse(BaseModel):
    dimension_key: str
    level: ImportanceLevelEnum
    weight: float

    @property
    def key(self) -> str:
        return self.dimension_key

    model_config = ConfigDict(from_attributes=True)

class ImportanceProfileResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    user_preference_profile_id: uuid.UUID
    importance_version: str
    completion_mode: ImportanceCompletionModeEnum
    created_at: datetime
    dimensions: List[ImportanceDimensionResponse]

    @field_validator("dimensions", mode="after")
    @classmethod
    def enforce_canonical_ordering(cls, dims: List[ImportanceDimensionResponse]) -> List[ImportanceDimensionResponse]:
        dim_map = {d.dimension_key: d for d in dims}
        ordered = []
        for key in CANONICAL_KEYS:
            if key in dim_map:
                ordered.append(dim_map[key])
        return ordered

    model_config = ConfigDict(from_attributes=True)

class MetaImportanceProfileResponse(BaseModel):
    version: str
    max_priority: int
    max_flexible: int
    weights: dict
    canonical_dimensions: List[str]
