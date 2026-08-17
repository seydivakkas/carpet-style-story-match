"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Source-Bound Story Presentation Domain Models.
Strict Pydantic v2 schemas defining citations, sections, and story presentation DTOs
bound strictly to validated cultural claims.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

SOURCE_BOUND_STORY_SCHEMA_VERSION = "source-bound-story-v1.0.0"
STORY_GROUNDING_POLICY_VERSION = "story-grounding-policy-v1.0.0"

FORBIDDEN_STORY_INFERRED_FIELDS = {
    "personalized_narrative", "user_psychology", "inferred_personality",
    "origin_authentication", "craftsman_intent"
}


class StoryCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citation_id: str
    claim_id: str
    evidence_unit_id: str
    source_id: str
    locator: str
    short_citation: str


class StorySection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str
    heading: str
    text: str
    claim_ids: List[str] = Field(..., description="Every section must reference at least one validated claim ID")
    citation_ids: List[str] = Field(default_factory=list)


class StoryPresentation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    story_id: str
    subject_id: str
    canonical_motif_key: str
    title: str
    summary: str
    sections: List[StorySection] = Field(default_factory=list)
    claim_ids: List[str] = Field(default_factory=list)
    citations: List[StoryCitation] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)
    claims_used: List[str] = Field(default_factory=list)
    claims_unused: List[str] = Field(default_factory=list)
    language: str = "tr"
    generation_mode: str = "TEMPLATE_ONLY"
    generator_version: str = Field(default=SOURCE_BOUND_STORY_SCHEMA_VERSION)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_story_inferred_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_STORY_INFERRED_FIELDS:
                    raise ValueError(f"Forbidden story field '{k}' detected in StoryPresentation.")
        return data
