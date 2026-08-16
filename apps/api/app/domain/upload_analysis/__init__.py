"""
User Upload Visual Analysis Domain Package (V2-02 & V2-03).
"""
from app.domain.upload_analysis.schemas import (
    UploadAnalysisResult,
    VisualObservation,
    VisualObservationType,
    VisualCategoryResult,
    CompositionEvidence,
    MotifCandidate,
    MotifCandidateStatus,
    AnalysisAbstention,
    AbstentionReasonCode,
    ModelProvenance,
    ProviderType,
    RegionEvidence,
    BoundingBox2D,
    Polygon2D,
    Point2D,
    SourceKind,
    QualityStatus,
    CanonicalizationStatus,
    FORBIDDEN_CULTURAL_FIELDS
)
from app.domain.upload_analysis.visual_categories import (
    VisualCategoryKey,
    CANONICAL_VISUAL_CATEGORIES,
    VISUAL_CATEGORY_TAXONOMY_VERSION
)
from app.domain.upload_analysis.motif_ontology import (
    VisualCandidateKey,
    DetectionMode,
    MOTIF_ONTOLOGY_DEFINITIONS,
    CANONICAL_PRODUCTION_MOTIFS,
    MOTIF_ONTOLOGY_VERSION
)
from app.domain.upload_analysis.validation import (
    validate_upload_analysis_result,
    validate_visual_category_key,
    validate_visual_candidate_key,
    ContractValidationError
)
from app.domain.upload_analysis.image_preparation import (
    prepare_image_for_vlm,
    PreparedInferenceImage,
    ImageValidationError
)
from app.domain.upload_analysis.vlm_provider import (
    MotifVisionProvider,
    VLLMOpenAICompatibleVisionProvider,
    RemoteOpenAICompatibleVisionProvider,
    FixtureVisionProvider,
    VLMProviderError,
    VLMAuthError,
    VLMTimeoutError,
    VLMMalformedOutputError
)
from app.domain.upload_analysis.service import (
    get_vlm_provider,
    get_vlm_provider_status,
    analyze_user_upload_image
)

__all__ = [
    # Schemas & Enums
    "UploadAnalysisResult",
    "VisualObservation",
    "VisualObservationType",
    "VisualCategoryResult",
    "CompositionEvidence",
    "MotifCandidate",
    "MotifCandidateStatus",
    "AnalysisAbstention",
    "AbstentionReasonCode",
    "ModelProvenance",
    "ProviderType",
    "RegionEvidence",
    "BoundingBox2D",
    "Polygon2D",
    "Point2D",
    "SourceKind",
    "QualityStatus",
    "CanonicalizationStatus",
    "FORBIDDEN_CULTURAL_FIELDS",
    # Visual Categories
    "VisualCategoryKey",
    "CANONICAL_VISUAL_CATEGORIES",
    "VISUAL_CATEGORY_TAXONOMY_VERSION",
    # Motif Ontology
    "VisualCandidateKey",
    "DetectionMode",
    "MOTIF_ONTOLOGY_DEFINITIONS",
    "CANONICAL_PRODUCTION_MOTIFS",
    "MOTIF_ONTOLOGY_VERSION",
    # Validation
    "validate_upload_analysis_result",
    "validate_visual_category_key",
    "validate_visual_candidate_key",
    "ContractValidationError",
    # Image Prep
    "prepare_image_for_vlm",
    "PreparedInferenceImage",
    "ImageValidationError",
    # VLM Providers
    "MotifVisionProvider",
    "VLLMOpenAICompatibleVisionProvider",
    "RemoteOpenAICompatibleVisionProvider",
    "FixtureVisionProvider",
    "VLMProviderError",
    "VLMAuthError",
    "VLMTimeoutError",
    "VLMMalformedOutputError",
    # Service Functions
    "get_vlm_provider",
    "get_vlm_provider_status",
    "analyze_user_upload_image",
]
