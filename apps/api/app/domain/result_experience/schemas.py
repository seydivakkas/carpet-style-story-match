"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Unified 5-Card Presentation Schemas for User Uploaded Carpet Analysis (V2-08).
"""
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

CANONICAL_RESULT_SCHEMA_VERSION = "unified-upload-result-v1.0.0"
MANDATORY_HISTORICAL_DISCLAIMER = "Görsel yakınlık tarihsel köken, dönem veya özgünlük doğrulaması değildir."


class ResultSectionState(str, Enum):
    """Section readiness and gating states."""
    READY = "READY"
    PARTIAL = "PARTIAL"
    WAITING_FOR_REVIEW = "WAITING_FOR_REVIEW"
    WAITING_FOR_RESEARCH = "WAITING_FOR_RESEARCH"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    BLOCKED_BY_QUALITY = "BLOCKED_BY_QUALITY"
    ERROR = "ERROR"


class BaseResultModel(BaseModel):
    """Base model enforcing strict Pydantic v2 configuration."""
    model_config = ConfigDict(extra="forbid", frozen=True)


class UploadedImageMeta(BaseResultModel):
    original_sha256: str
    prepared_sha256: Optional[str] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    primary_image_url: str


class ColorItem(BaseResultModel):
    label: str
    hex_code: Optional[str] = None
    coverage_percentage: float
    turkish_description: str


class CatalogVisualMatchItem(BaseResultModel):
    rank: int
    catalog_id: str
    sku: str
    brand: Optional[str] = None
    collection: Optional[str] = None
    product_name: str
    primary_image_url: Optional[str] = None
    visual_proximity_score: float
    closest_dimensions: List[str] = Field(default_factory=list)


class VisualCharacterCard(BaseResultModel):
    """Card 1 — Görsel Karakter"""
    state: ResultSectionState
    style_dna_version: str = "style-dna-v1.0.0"
    dimensions: Dict[str, float] = Field(default_factory=dict)
    palette: List[ColorItem] = Field(default_factory=list)
    composition: Dict[str, Any] = Field(default_factory=dict)
    catalog_matches: List[CatalogVisualMatchItem] = Field(default_factory=list)


class MotifCandidateItem(BaseResultModel):
    candidate_id: str
    visual_descriptor: str
    turkish_label: str
    ai_confidence: float
    bounding_box: Optional[List[float]] = None
    status: str  # AI_CANDIDATE | WAITING_FOR_REVIEW | AUTO_CONFIRMED | CURATOR_CONFIRMED | UNCERTAIN | REJECTED
    confirmed_canonical_motif_key: Optional[str] = None


class MotifReviewSummary(BaseResultModel):
    total_candidates: int
    confirmed_count: int
    pending_count: int
    uncertain_count: int
    rejected_count: int


class MotifCard(BaseResultModel):
    """Card 2 — Motifler"""
    state: ResultSectionState
    candidates: List[MotifCandidateItem] = Field(default_factory=list)
    review_summary: MotifReviewSummary


class ClaimSourceItem(BaseResultModel):
    institution: str
    title: str
    locator: str
    excerpt: Optional[str] = None
    canonical_url: Optional[str] = None


class CulturalClaimItem(BaseResultModel):
    claim_id: str
    status: str  # DOCUMENTED | CONTEXTUAL | CONTESTED | UNKNOWN
    statement_tr: str
    scope: Optional[str] = None
    sources: List[ClaimSourceItem] = Field(default_factory=list)


class CulturalContextCard(BaseResultModel):
    """Card 3 — Kültürel Bağlam"""
    state: ResultSectionState
    user_message: Optional[str] = None
    claims: List[CulturalClaimItem] = Field(default_factory=list)


class StorySectionItem(BaseResultModel):
    heading: str
    content: str
    citations: List[str] = Field(default_factory=list)
    is_contested: bool = False


class SourceBoundStoryItem(BaseResultModel):
    title: str
    summary: str
    sections: List[StorySectionItem] = Field(default_factory=list)


class ThematicAffinityItem(BaseResultModel):
    matched_themes: List[str] = Field(default_factory=list)
    affinity_description: str


class MotifStoryCard(BaseResultModel):
    """Card 4 — Motif Hikâyeleri"""
    state: ResultSectionState
    user_message: Optional[str] = None
    story: Optional[SourceBoundStoryItem] = None
    thematic_affinity: Optional[ThematicAffinityItem] = None


class HistoricalVisualMatchItem(BaseResultModel):
    rank: int
    historical_reference_id: str
    reference_key: str
    institution: str
    object_title: str
    museum_object_id: Optional[str] = None
    canonical_source_url: Optional[str] = None
    primary_image_url: Optional[str] = None
    date_or_period: Optional[str] = None
    origin_culture: Optional[str] = None
    origin_geography: Optional[str] = None
    medium_materials: Optional[str] = None
    visual_proximity_score: float
    closest_dimensions: List[str] = Field(default_factory=list)


class HistoricalConnectionsCard(BaseResultModel):
    """Card 5 — Tarihsel Bağlantılar"""
    state: ResultSectionState
    disclaimer: str = MANDATORY_HISTORICAL_DISCLAIMER
    matches: List[HistoricalVisualMatchItem] = Field(default_factory=list)


class ResultProvenance(BaseResultModel):
    analysis_contract_version: str = "upload-analysis-v1.0.0"
    style_dna_version: str = "style-dna-v1.0.0"
    color_version: str = "color-observation-v1.0.0"
    vlm_provider_version: Optional[str] = None
    review_version: Optional[str] = "motif-review-v1.0.0"
    evidence_version: Optional[str] = "evidence-rag-v1.0.0"
    claim_version: Optional[str] = "cultural-claim-v1.0.0"
    story_version: Optional[str] = "source-bound-story-v1.0.0"
    visual_retrieval_version: str = "visual-retrieval-v1.0.0"
    catalog_corpus_fingerprint: Optional[str] = None
    historical_corpus_fingerprint: Optional[str] = None


class UnifiedUploadResult(BaseResultModel):
    """Master 5-Card Unified Upload Result DTO (V2-08)."""
    schema_version: str = CANONICAL_RESULT_SCHEMA_VERSION
    analysis_id: uuid.UUID
    image_meta: UploadedImageMeta
    visual_character: VisualCharacterCard
    motifs: MotifCard
    cultural_context: CulturalContextCard
    motif_story: MotifStoryCard
    historical_connections: HistoricalConnectionsCard
    provenance: ResultProvenance
    warnings: List[str] = Field(default_factory=list)


class AcceptedAnalysisResponse(BaseResultModel):
    analysis_id: uuid.UUID
    status: str = "PROCESSING"
    poll_url: str


class AnalysisStatusResponse(BaseResultModel):
    analysis_id: uuid.UUID
    status: str
    error: Optional[str] = None
