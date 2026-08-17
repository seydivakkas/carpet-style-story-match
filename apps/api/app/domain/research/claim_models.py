"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Cultural Claim Domain Models.
Strict Pydantic v2 schemas defining claim candidates, relation links,
claim scopes, and validated cultural claims bound strictly to EvidencePack evidence.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.domain.research.models import SourceTier

CULTURAL_CLAIM_SCHEMA_VERSION = "cultural-claim-v1.0.0"
CULTURAL_CLAIM_VALIDATOR_VERSION = "cultural-claim-validator-v1.0.0"

FORBIDDEN_CLAIM_TEXT_WORDS = {
    "always", "universally", "definitely", "proves", "authenticates", "guarantees"
}

FORBIDDEN_CLAIM_INFERRED_FIELDS = {
    "truth_score", "cultural_confidence", "historical_probability", "symbolism_probability"
}


class CulturalClaimStatus(str, Enum):
    DOCUMENTED = "DOCUMENTED"
    CONTEXTUAL = "CONTEXTUAL"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"


class ClaimRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTEXT_LIMITED_SUPPORT = "CONTEXT_LIMITED_SUPPORT"
    CONTRADICTS = "CONTRADICTS"
    IRRELEVANT = "IRRELEVANT"


class ClaimScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    region: Optional[str] = None
    period: Optional[str] = None
    tradition: Optional[str] = None
    institutional_context: Optional[str] = None
    object_context: Optional[str] = None
    other_scope_note: Optional[str] = None


class ClaimEvidenceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_unit_id: str
    relation: ClaimRelation
    scope_note: Optional[str] = None
    source_tier: SourceTier
    locator: str = Field(..., description="Mandatory locator for traceability")


class CulturalClaimCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    subject_id: str
    canonical_motif_key: str
    proposed_statement: str
    proposed_scope: Optional[ClaimScope] = None
    source_reference: Optional[str] = None


class ValidatedCulturalClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    subject_id: str
    canonical_motif_key: str
    statement: str
    status: CulturalClaimStatus
    scope: Optional[ClaimScope] = None
    evidence_links: List[ClaimEvidenceLink] = Field(default_factory=list)
    evidence_unit_ids: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)
    reasoning_summary: str
    limitations: List[str] = Field(default_factory=list)
    language: str = "tr"
    validator_version: str = Field(default=CULTURAL_CLAIM_VALIDATOR_VERSION)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_numeric_truth_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CLAIM_INFERRED_FIELDS:
                    raise ValueError(f"Forbidden numeric truth field '{k}' detected in ValidatedCulturalClaim.")
        return data
