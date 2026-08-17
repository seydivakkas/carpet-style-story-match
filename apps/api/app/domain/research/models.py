"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Evidence RAG & Source Research Engine Domain Models.
Strict Pydantic v2 schemas defining research subjects, query plans,
source documents, evidence units, conflicts, and evidence packs.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

EVIDENCE_PACK_SCHEMA_VERSION = "evidence-pack-v1.0.0"
RESEARCH_QUERY_PLAN_VERSION = "cultural-research-query-v1.0.0"

FORBIDDEN_EVIDENCE_PACK_FIELDS = {
    "final_claim", "symbolic_meaning", "story", "cultural_truth",
    "narrative_prose", "personalized_explanation", "cultural_claim"
}

FORBIDDEN_SUBJECT_INFERRED_FIELDS = {
    "predicted_culture", "predicted_dynasty", "predicted_origin", "predicted_religion"
}


class SourceTier(str, Enum):
    TIER_1_PRIMARY_INSTITUTIONAL = "TIER_1_PRIMARY_INSTITUTIONAL"
    TIER_2_SCHOLARLY = "TIER_2_SCHOLARLY"
    TIER_3_REPUTABLE_SECONDARY = "TIER_3_REPUTABLE_SECONDARY"
    REJECTED_SOURCE = "REJECTED_SOURCE"


class ResearchVerificationStatus(str, Enum):
    CURATOR_CONFIRMED = "CURATOR_CONFIRMED"
    VERIFIED_CANONICAL = "VERIFIED_CANONICAL"
    # Unverified states (rejected for research input):
    AI_CANDIDATE = "AI_CANDIDATE"
    UNMAPPED_MOTIF_CANDIDATE = "UNMAPPED_MOTIF_CANDIDATE"
    ABSTAINED = "ABSTAINED"


class ResearchSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: str
    canonical_motif_key: str
    verification_status: ResearchVerificationStatus = ResearchVerificationStatus.CURATOR_CONFIRMED
    display_name: str
    ontology_version: str = "motif-ontology-v1.0.0"
    visual_evidence_ref: Optional[str] = None
    known_source_context: Optional[Dict[str, Any]] = None
    created_at: str

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_inferred_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_SUBJECT_INFERRED_FIELDS:
                    raise ValueError(f"Forbidden inferred context field '{k}' detected in ResearchSubject.")
        return data


class ResearchQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_plan_id: str
    query_plan_version: str = RESEARCH_QUERY_PLAN_VERSION
    subject_id: str
    canonical_motif_key: str
    queries: List[str] = Field(..., min_length=1)
    created_at: str


class ResearchSourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    canonical_url: str
    title: str
    institution_or_publisher: str
    source_type: str
    source_tier: SourceTier
    publication_date: Optional[str] = None
    retrieved_at: str
    language: str = "tr"
    content_sha256: str
    access_status: str = "ACCESSIBLE"
    rights_note: Optional[str] = "Educational/Research Fair Use"
    provenance: Dict[str, Any] = Field(default_factory=dict)


class EvidenceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    source_id: str
    subject_motif_key: str
    locator: str = Field(..., description="Mandatory locator for traceability: e.g. page number, catalog ID, object ID, section heading")
    supporting_excerpt: str = Field(..., description="Copyright-safe short excerpt, max 300 chars")
    normalized_summary: str
    language: str = "tr"
    retrieval_score: float = Field(..., ge=0.0, le=1.0)
    source_tier: SourceTier
    content_hash: str

    @model_validator(mode="after")
    def validate_excerpt_length(self) -> "EvidenceUnit":
        if len(self.supporting_excerpt) > 500:
            raise ValueError("Supporting excerpt exceeds maximum copyright-safe limit of 500 characters.")
        if not self.locator or not self.locator.strip():
            raise ValueError("EvidenceUnit requires a non-empty locator for strict traceability.")
        return self


class EvidenceConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conflict_id: str
    subject_motif_key: str
    evidence_unit_ids: List[str] = Field(..., min_length=2)
    conflict_type: str
    description: str


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(default=EVIDENCE_PACK_SCHEMA_VERSION)
    research_run_id: str
    subject: ResearchSubject
    query_plan: ResearchQueryPlan
    sources: List[ResearchSourceDocument] = Field(default_factory=list)
    evidence_units: List[EvidenceUnit] = Field(default_factory=list)
    contradictions: List[EvidenceConflict] = Field(default_factory=list)
    coverage: Dict[str, Any]
    provenance: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_story_claim_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_EVIDENCE_PACK_FIELDS:
                    raise ValueError(f"Forbidden field '{k}' detected in EvidencePack. EvidencePack must NOT contain claims or stories.")
        return data
