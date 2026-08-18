"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Visual Retrieval Domain Models v1.0.0
Strict, immutable Pydantic v2 schemas for Catalog and Historical visual proximity retrieval.
"""
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

CANONICAL_STYLE_DNA_VERSION = "style-dna-v1.0.0"
CANONICAL_RETRIEVAL_VERSION = "visual-retrieval-v1.0.0"
CANONICAL_POLICY_VERSION = "visual-retrieval-policy-v1.0.0"

CANONICAL_DIMENSION_KEYS = [
    "color_energy",
    "color_diversity",
    "contrast",
    "warmth",
    "visual_complexity",
    "structural_order",
    "rhythm_repetition",
    "focal_strength",
    "form_language",
]


class QuerySourceType(str, Enum):
    USER_UPLOAD = "USER_UPLOAD"
    CATALOG_IMAGE = "CATALOG_IMAGE"
    HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"
    DIRECT_VECTOR = "DIRECT_VECTOR"


class StyleDimensionKey(str, Enum):
    COLOR_ENERGY = "color_energy"
    COLOR_DIVERSITY = "color_diversity"
    CONTRAST = "contrast"
    WARMTH = "warmth"
    VISUAL_COMPLEXITY = "visual_complexity"
    STRUCTURAL_ORDER = "structural_order"
    RHYTHM_REPETITION = "rhythm_repetition"
    FOCAL_STRENGTH = "focal_strength"
    FORM_LANGUAGE = "form_language"


class StyleDimensionValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension_key: StyleDimensionKey
    value: float = Field(..., ge=0.0, le=1.0, description="Normalized dimension magnitude between 0.0 and 1.0")


class VisualRetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style_dna: Union[Dict[str, float], List[StyleDimensionValue]] = Field(
        ...,
        description="Exactly 9 canonical Style DNA dimensions with values in [0.0, 1.0]"
    )
    style_dna_version: str = Field(
        default=CANONICAL_STYLE_DNA_VERSION,
        description="Frozen Style DNA algorithm version"
    )
    query_id: Optional[str] = Field(default=None, description="Optional client or session query identifier")
    query_source_type: QuerySourceType = Field(
        default=QuerySourceType.DIRECT_VECTOR,
        description="Provenance classification of input query vector"
    )
    exclude_id: Optional[str] = Field(
        default=None,
        description="Optional candidate or reference ID to exclude from self-matching"
    )

    @field_validator("style_dna_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CANONICAL_STYLE_DNA_VERSION:
            raise ValueError(
                f"Unsupported Style DNA version '{v}'. Required version is '{CANONICAL_STYLE_DNA_VERSION}'."
            )
        return v

    @field_validator("style_dna")
    @classmethod
    def validate_style_dna(cls, v: Union[Dict[str, float], List[StyleDimensionValue]]) -> Dict[str, float]:
        if isinstance(v, list):
            dna_dict: Dict[str, float] = {}
            for item in v:
                key = item.dimension_key.value if hasattr(item.dimension_key, "value") else str(item.dimension_key)
                if key in dna_dict:
                    raise ValueError(f"Duplicate dimension key '{key}' in style_dna list.")
                dna_dict[key] = item.value
        elif isinstance(v, dict):
            dna_dict = dict(v)
        else:
            raise ValueError("style_dna must be a dict or list of StyleDimensionValue objects.")

        provided_keys = set(dna_dict.keys())
        expected_keys = set(CANONICAL_DIMENSION_KEYS)

        missing = expected_keys - provided_keys
        extra = provided_keys - expected_keys

        if missing:
            raise ValueError(f"Missing required Style DNA dimensions: {sorted(list(missing))}")
        if extra:
            raise ValueError(f"Unknown or extra Style DNA dimensions forbidden: {sorted(list(extra))}")

        for k, val in dna_dict.items():
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"Dimension '{k}' value must be a float, got {type(val).__name__}.")
            if val < 0.0 or val > 1.0:
                raise ValueError(f"Dimension '{k}' value {val} out of valid bounds [0.0, 1.0].")

        return {k: round(float(dna_dict[k]), 4) for k in CANONICAL_DIMENSION_KEYS}


class StyleDimensionDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension_key: str
    query_value: float
    candidate_value: float
    absolute_delta: float
    normalized_delta: float


class CatalogVisualMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1, description="1-indexed visual proximity rank")
    catalog_id: str = Field(..., description="Unique UUID string of the catalog carpet")
    sku: str = Field(..., description="Official brand SKU")
    brand: str = Field(..., description="Official carpet brand name")
    collection: Optional[str] = Field(default=None, description="Official collection name if available")
    product_name: str = Field(..., description="Official product title")
    primary_image_url: Optional[str] = Field(default=None, description="Public/protected primary image URL")
    visual_proximity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Deterministic visual proximity score (100 = identical 9D Style DNA)"
    )
    style_dimension_deltas: List[StyleDimensionDelta] = Field(
        ...,
        description="Per-dimension deltas between query and candidate"
    )
    closest_dimensions: List[str] = Field(
        ...,
        description="Top 3 dimensions with highest visual similarity (smallest deltas)"
    )
    largest_differences: List[str] = Field(
        ...,
        description="Top 2 dimensions with largest visual differences (largest deltas)"
    )
    style_dna_version: str = Field(default=CANONICAL_STYLE_DNA_VERSION)
    source_metadata_provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance of product metadata assertions"
    )


class HistoricalVisualMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1, description="1-indexed visual proximity rank")
    historical_reference_id: str = Field(..., description="Unique UUID string of the historical reference")
    reference_key: str = Field(..., description="Human-readable reference key (e.g. hist-met-001)")
    institution: str = Field(..., description="Holding museum or institution name")
    object_title: str = Field(..., description="Official museum object title")
    museum_object_id: Optional[str] = Field(default=None, description="Museum accession/inventory ID")
    canonical_source_url: Optional[str] = Field(default=None, description="Official museum permalink")
    primary_image_url: Optional[str] = Field(default=None, description="Primary image URL if available")
    museum_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source/museum documented metadata (date, culture, geography, medium)"
    )
    visual_proximity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Deterministic visual proximity score (100 = identical 9D Style DNA)"
    )
    style_dimension_deltas: List[StyleDimensionDelta] = Field(
        ...,
        description="Per-dimension deltas between query and candidate"
    )
    closest_dimensions: List[str] = Field(
        ...,
        description="Top 3 dimensions with highest visual similarity (smallest deltas)"
    )
    largest_differences: List[str] = Field(
        ...,
        description="Top 2 dimensions with largest visual differences (largest deltas)"
    )
    style_dna_version: str = Field(default=CANONICAL_STYLE_DNA_VERSION)
    metadata_provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance asserting museum metadata as source assertions"
    )


class CatalogCorpusAccounting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_records: int = Field(..., description="Total catalog products in database")
    eligible_records: int = Field(..., description="Catalog products eligible for visual ranking")
    excluded_partial: int = Field(..., description="Products excluded due to PARTIAL Style DNA status")
    excluded_missing_primary_image: int = Field(..., description="Products excluded due to missing primary image")
    excluded_missing_style_dna: int = Field(..., description="Products excluded due to missing Style DNA profile")
    corpus_fingerprint: str = Field(..., description="Deterministic SHA-256 fingerprint of eligible catalog corpus")


class HistoricalCorpusAccounting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_records: int = Field(..., description="Total historical references in database")
    eligible_records: int = Field(..., description="Historical references eligible for visual ranking")
    excluded_missing_primary_image: int = Field(..., description="Historical references excluded due to missing image")
    excluded_missing_style_dna: int = Field(..., description="Historical references excluded due to missing Style DNA")
    corpus_fingerprint: str = Field(..., description="Deterministic SHA-256 fingerprint of eligible historical corpus")


class VisualRetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval_version: str = Field(default=CANONICAL_RETRIEVAL_VERSION)
    retrieval_policy_version: str = Field(default=CANONICAL_POLICY_VERSION)
    query_provenance: Dict[str, Any] = Field(..., description="Input query metadata and provenance assertions")
    catalog_corpus_accounting: CatalogCorpusAccounting = Field(..., description="Catalog corpus eligibility metrics")
    historical_corpus_accounting: HistoricalCorpusAccounting = Field(..., description="Historical corpus eligibility metrics")
    catalog_matches: List[CatalogVisualMatch] = Field(..., description="Top ranked catalog visual proximity matches")
    historical_matches: List[HistoricalVisualMatch] = Field(..., description="Top ranked historical visual proximity matches")
