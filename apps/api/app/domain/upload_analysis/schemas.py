"""
User Upload Analysis Contract Schemas (v1.0.0).

Strict Pydantic v2 schemas defining allowed visual evidence, composition,
observations, motif candidates, abstentions, and model provenance.
FORBIDS all cultural, origin, dynasty, story, or personality fields.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.domain.upload_analysis.visual_categories import (
    VisualCategoryKey,
    VISUAL_CATEGORY_TAXONOMY_VERSION,
    CANONICAL_VISUAL_CATEGORIES
)
from app.domain.upload_analysis.motif_ontology import (
    MotifFamily,
    MotifType,
    DetectionMode,
    VisualCandidateKey,
    MOTIF_ONTOLOGY_VERSION,
    CANONICAL_PRODUCTION_MOTIFS
)

UPLOAD_ANALYSIS_SCHEMA_VERSION = "upload-analysis-v1.0.0"

# List of forbidden cultural / non-visual attribute keys
FORBIDDEN_CULTURAL_FIELDS = {
    "culture", "cultural_origin", "dynasty", "historical_period",
    "symbolism", "meaning", "story", "personality", "ethnicity",
    "religion", "authentication", "authenticated_origin", "verified_period",
    "verified_culture", "predicted_brand", "predicted_collection",
    "predicted_merinos_collection", "spiritual_meaning", "blessing"
}


class CoordinateSpace(str, Enum):
    ORIGINAL_IMAGE = "ORIGINAL_IMAGE"
    CANONICAL_CARPET = "CANONICAL_CARPET"
    NORMALIZED_CANONICAL = "NORMALIZED_CANONICAL"


class SourceKind(str, Enum):
    USER_UPLOAD = "USER_UPLOAD"
    CATALOG_IMAGE = "CATALOG_IMAGE"


class QualityStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    BLOCK = "BLOCK"
    UNKNOWN = "UNKNOWN"


class CanonicalizationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderType(str, Enum):
    LOCAL_VLLM = "LOCAL_VLLM"
    REMOTE_OPENAI_COMPATIBLE = "REMOTE_OPENAI_COMPATIBLE"
    TEST_FIXTURE = "TEST_FIXTURE"


class VisualObservationType(str, Enum):
    COLOR = "COLOR"
    FORM = "FORM"
    EDGE = "EDGE"
    SYMMETRY = "SYMMETRY"
    REPETITION = "REPETITION"
    COMPOSITION = "COMPOSITION"
    REGION_STRUCTURE = "REGION_STRUCTURE"
    SHAPE = "SHAPE"
    TEXTURE = "TEXTURE"
    FOCAL_STRUCTURE = "FOCAL_STRUCTURE"
    OTHER_VISUAL = "OTHER_VISUAL"


class MotifCandidateStatus(str, Enum):
    AI_CANDIDATE = "AI_CANDIDATE"
    UNMAPPED_MOTIF_CANDIDATE = "UNMAPPED_MOTIF_CANDIDATE"
    ABSTAINED = "ABSTAINED"
    # Reserved future review outcomes (cannot be emitted by model directly):
    CURATOR_CONFIRMED = "CURATOR_CONFIRMED"
    UNCERTAIN = "UNCERTAIN"
    REJECTED = "REJECTED"


class AbstentionReasonCode(str, Enum):
    IMAGE_QUALITY_INSUFFICIENT = "IMAGE_QUALITY_INSUFFICIENT"
    CARPET_REGION_UNRESOLVED = "CARPET_REGION_UNRESOLVED"
    MOTIF_VISUALLY_AMBIGUOUS = "MOTIF_VISUALLY_AMBIGUOUS"
    ONTOLOGY_NO_MATCH = "ONTOLOGY_NO_MATCH"
    OCCLUDED_REGION = "OCCLUDED_REGION"
    CROPPED_REGION = "CROPPED_REGION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    OTHER = "OTHER"


class Point2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class Polygon2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: List[Point2D] = Field(..., min_length=3)


class BoundingBox2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox2D":
        if self.x_min > self.x_max:
            raise ValueError(f"x_min ({self.x_min}) cannot be greater than x_max ({self.x_max})")
        if self.y_min > self.y_max:
            raise ValueError(f"y_min ({self.y_min}) cannot be greater than y_max ({self.y_max})")
        return self


class RegionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coordinate_space: CoordinateSpace = CoordinateSpace.NORMALIZED_CANONICAL
    bounding_box: Optional[BoundingBox2D] = None
    polygon: Optional[Polygon2D] = None
    region_label: Optional[str] = None


class VisualObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_id: str
    observation_type: VisualObservationType
    region: Optional[RegionEvidence] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str
    evidence_features: List[str] = Field(default_factory=list)
    source: str = "vlm_observation"

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_cultural_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CULTURAL_FIELDS:
                    raise ValueError(f"Forbidden cultural/non-visual field '{k}' is rejected in Upload Analysis Contract.")
        return data


class VisualCategoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_key: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_observation_ids: List[str] = Field(default_factory=list)
    secondary_categories: List[str] = Field(default_factory=list)
    status: str = "CLASSIFIED"
    abstention_reason: Optional[str] = None


class CompositionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    central_focus: Optional[float] = Field(None, ge=0.0, le=1.0)
    border_dominance: Optional[float] = Field(None, ge=0.0, le=1.0)
    vertical_symmetry: Optional[float] = Field(None, ge=0.0, le=1.0)
    horizontal_symmetry: Optional[float] = Field(None, ge=0.0, le=1.0)
    rotational_structure: Optional[float] = Field(None, ge=0.0, le=1.0)
    repetition_strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    field_organization: Optional[str] = None
    evidence_observation_ids: List[str] = Field(default_factory=list)


class ModelProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_type: ProviderType = ProviderType.TEST_FIXTURE
    model_id: str
    model_version: str
    prompt_version: str
    inference_timestamp: str
    request_hash: Optional[str] = None


class MotifCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    visual_candidate_key: str
    proposed_canonical_motif_key: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    region: Optional[RegionEvidence] = None
    visual_evidence: List[str] = Field(default_factory=list)
    status: MotifCandidateStatus = MotifCandidateStatus.AI_CANDIDATE
    model_provenance: Optional[ModelProvenance] = None
    abstention_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_model_cannot_confirm(self) -> "MotifCandidate":
        if self.status == MotifCandidateStatus.CURATOR_CONFIRMED:
            raise ValueError(
                "Model-originated MotifCandidate cannot directly set CURATOR_CONFIRMED. "
                "AI candidates must be flagged as AI_CANDIDATE or UNMAPPED_MOTIF_CANDIDATE."
            )
        return self


class AnalysisAbstention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(..., description="Scope of abstention e.g. overall, visual_category, motif_candidate")
    reason_code: AbstentionReasonCode
    message: str
    related_region: Optional[RegionEvidence] = None
    related_candidate_id: Optional[str] = None


class UploadAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(default=UPLOAD_ANALYSIS_SCHEMA_VERSION)
    analysis_id: str
    image_asset_id: str
    image_sha256: str
    source_kind: SourceKind = SourceKind.USER_UPLOAD
    quality_status: QualityStatus = QualityStatus.PASS
    canonicalization_status: CanonicalizationStatus = CanonicalizationStatus.AVAILABLE
    style_dna_reference: Optional[str] = "style-dna-v1.0.0"
    visual_observations: List[VisualObservation] = Field(default_factory=list)
    visual_category: VisualCategoryResult
    composition_evidence: CompositionEvidence
    motif_candidates: List[MotifCandidate] = Field(default_factory=list)
    abstentions: List[AnalysisAbstention] = Field(default_factory=list)
    provenance: ModelProvenance

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_cultural_keys_top_level(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CULTURAL_FIELDS:
                    raise ValueError(f"Forbidden cultural/non-visual field '{k}' is rejected in UploadAnalysisResult contract.")
        return data
