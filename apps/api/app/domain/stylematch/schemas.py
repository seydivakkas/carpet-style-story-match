"""Pydantic schemas for Visual Style Match Engine."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.preference_assessment import (
    StyleMatchStatusEnum,
    StyleMatchLabelEnum,
    ImportanceLevelEnum,
    UserPreferenceProvenanceEnum
)

class StyleMatchCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carpet_style_profile_id: uuid.UUID = Field(..., description="Target carpet style profile UUID")

class StyleMatchDimensionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension_key: str
    user_value: Optional[float] = None
    user_provenance: Optional[UserPreferenceProvenanceEnum] = None
    carpet_value: Optional[float] = None
    carpet_dimension_status: Optional[str] = None
    importance_level: ImportanceLevelEnum
    importance_weight: float
    difference: Optional[float] = None
    similarity: Optional[float] = None
    weighted_similarity: Optional[float] = None
    weighted_difference: Optional[float] = None
    comparable: bool
    user_preference_confidence: Optional[float] = None
    carpet_measurement_confidence: Optional[float] = None

class StyleMatchExplanationMatch(BaseModel):
    dimension_key: str
    similarity: float
    importance_level: ImportanceLevelEnum
    importance_weight: float
    user_value: float
    carpet_value: float
    narrative: str

class StyleMatchExplanationDifference(BaseModel):
    dimension_key: str
    difference: float
    similarity: float
    importance_level: ImportanceLevelEnum
    importance_weight: float
    impact: float
    narrative: str

class StyleMatchExplanationResponse(BaseModel):
    top_matches: List[StyleMatchExplanationMatch] = Field(default_factory=list)
    main_differences: List[StyleMatchExplanationDifference] = Field(default_factory=list)
    coverage_notes: List[str] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)

class VisualStyleMatchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assessment_id: uuid.UUID
    user_preference_profile_id: uuid.UUID
    importance_profile_id: uuid.UUID
    carpet_style_profile_id: uuid.UUID
    match_version: str
    status: StyleMatchStatusEnum
    score: Optional[float] = None
    score_100: Optional[float] = None
    match_label: Optional[StyleMatchLabelEnum] = None
    match_label_tr: Optional[str] = None
    comparable_dimension_count: int
    weighted_coverage: float
    total_importance_weight: float
    comparable_weight: float
    dimensions: List[StyleMatchDimensionResponse]
    explanation: StyleMatchExplanationResponse
    created_at: datetime
