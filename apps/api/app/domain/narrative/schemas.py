"""Pydantic schemas for User Narrative Profile."""
from datetime import datetime
from typing import Dict, List
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.preference_assessment import NarrativeInterestLevelEnum, NarrativeCompletionModeEnum


class NarrativeSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skip: bool = Field(
        default=False,
        description="Set to true if user chooses to skip narrative theme selection"
    )
    primary_themes: List[str] = Field(
        default_factory=list,
        description="List of primary narrative theme keys (max 3)"
    )
    secondary_themes: List[str] = Field(
        default_factory=list,
        description="List of secondary narrative theme keys (max 3)"
    )


class UserNarrativeThemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str = Field(description="Canonical theme key e.g. nature_growth")
    interest_level: NarrativeInterestLevelEnum = Field(description="PRIMARY, SECONDARY, or NOT_SELECTED")
    interest_weight: float = Field(description="Numeric interest weight: PRIMARY=1.00, SECONDARY=0.60, NOT_SELECTED=0.00")


class UserNarrativeProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assessment_id: uuid.UUID
    user_preference_profile_id: uuid.UUID
    profile_version: str
    completion_mode: NarrativeCompletionModeEnum
    created_at: datetime
    themes: List[UserNarrativeThemeResponse] = Field(
        description="Exactly 8 narrative themes in canonical N1->N8 order"
    )


class MetaNarrativeProfileResponse(BaseModel):
    version: str = Field(default="user-narrative-profile-v1")
    levels: Dict[str, float] = Field(
        default_factory=lambda: {
            "PRIMARY": 1.0,
            "SECONDARY": 0.6,
            "NOT_SELECTED": 0.0
        }
    )
    max_primary: int = Field(default=3)
    max_secondary: int = Field(default=3)
    skip_supported: bool = Field(default=True)
