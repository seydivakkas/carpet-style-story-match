"""Domain schemas and enums for external carpet dataset intake & role classification v1."""
from datetime import datetime, timezone
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ExternalDatasetRole(str, enum.Enum):
    CATALOG_CANDIDATE = "CATALOG_CANDIDATE"
    HISTORICAL_CANDIDATE = "HISTORICAL_CANDIDATE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    BENCHMARK_ONLY = "BENCHMARK_ONLY"
    QUARANTINE = "QUARANTINE"


class CatalogEligibility(str, enum.Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class HistoricalEligibility(str, enum.Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DatasetProviderType(str, enum.Enum):
    OFFICIAL_MANUFACTURER = "OFFICIAL_MANUFACTURER"
    MUSEUM = "MUSEUM"
    ARCHIVE = "ARCHIVE"
    ACADEMIC_DATASET = "ACADEMIC_DATASET"
    KAGGLE = "KAGGLE"
    ROBOFLOW = "ROBOFLOW"
    GITHUB = "GITHUB"
    INTERNAL = "INTERNAL"
    OTHER = "OTHER"


class DatasetLabelType(str, enum.Enum):
    PATTERN_FAMILY = "PATTERN_FAMILY"
    CONSTRUCTION = "CONSTRUCTION"
    MOTIF_VISUAL = "MOTIF_VISUAL"
    PERIOD_SOURCE_LABEL = "PERIOD_SOURCE_LABEL"
    REGION_SOURCE_LABEL = "REGION_SOURCE_LABEL"
    PRODUCT_COLLECTION = "PRODUCT_COLLECTION"
    OTHER = "OTHER"


class LabelMappingStatus(str, enum.Enum):
    CURATOR_CONFIRMED = "CURATOR_CONFIRMED"
    UNMAPPED = "UNMAPPED"


class ImageValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID_IMAGE = "INVALID_IMAGE"
    UNCHECKED = "UNCHECKED"


class DatasetRegistryEntry(BaseModel):
    dataset_key: str = Field(..., description="Unique slug for the dataset e.g. iranian-patterns")
    dataset_name: str = Field(..., description="Human readable dataset title")
    provider: str = Field(..., description="Provider name e.g. Kaggle / Merinos / The Met")
    provider_type: DatasetProviderType = Field(..., description="Canonical provider type")
    source_url: str = Field(..., description="Official URL or homepage of the dataset")
    source_reference: Optional[str] = Field(None, description="Additional provenance reference")
    license_name: str = Field(..., description="Dataset license name e.g. CC0-1.0, MIT, Proprietary")
    license_url: Optional[str] = Field(None, description="License text URL")
    license_verified: bool = Field(False, description="True if license rights permit intended consumption")
    retrieved_at: str = Field(..., description="ISO 8601 UTC timestamp of retrieval")
    declared_task: Optional[str] = Field(None, description="Declared task e.g. pattern_classification")
    declared_categories: List[str] = Field(default_factory=list)
    image_count_declared: Optional[int] = Field(None)
    image_count_observed: int = Field(0)
    contains_originals: bool = Field(True)
    contains_augmentations: bool = Field(False)
    contains_synthetic: bool = Field(False)
    default_role: ExternalDatasetRole = Field(ExternalDatasetRole.RESEARCH_ONLY)
    notes: Optional[str] = Field(None)


class DatasetRegistry(BaseModel):
    schema_version: str = "external-dataset-registry-v1"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    datasets: List[DatasetRegistryEntry] = Field(default_factory=list)


class ManifestRecord(BaseModel):
    record_id: str = Field(..., description="Unique record ID e.g. dataset_key:hash_or_id")
    dataset_key: str = Field(..., description="Dataset key reference")
    relative_image_path: str = Field(..., description="Path relative to dataset raw root")
    content_sha256: str = Field(..., description="SHA-256 hash of image file bytes")
    perceptual_hash_optional: Optional[str] = Field(None, description="Optional pHash string")
    original_source_url: Optional[str] = Field(None)
    original_object_id: Optional[str] = Field(None)
    provider_record_id: Optional[str] = Field(None)
    source_label: Optional[str] = Field(None)
    namespaced_label: Optional[str] = Field(None, description="Form: dataset_key:source_label")
    label_type: Optional[DatasetLabelType] = Field(None)
    canonical_label: Optional[str] = Field(None)
    source_split: Optional[str] = Field(None, description="train/val/test")
    is_original: bool = Field(True)
    is_augmented: bool = Field(False)
    is_synthetic: bool = Field(False)
    augmentation_parent_id: Optional[str] = Field(None)
    license_name: str = Field("Unknown")
    license_verified: bool = Field(False)
    classified_role: ExternalDatasetRole = Field(ExternalDatasetRole.QUARANTINE)
    catalog_eligibility: CatalogEligibility = Field(CatalogEligibility.INELIGIBLE)
    historical_eligibility: HistoricalEligibility = Field(HistoricalEligibility.INELIGIBLE)
    classification_reasons: List[str] = Field(default_factory=list)
    review_status: str = Field("UNREVIEWED")
    image_validation_status: ImageValidationStatus = Field(ImageValidationStatus.UNCHECKED)
    manufacturer: Optional[str] = Field(None)
    official_sku: Optional[str] = Field(None)
    institution: Optional[str] = Field(None)
    image_width: Optional[int] = Field(None)
    image_height: Optional[int] = Field(None)


class LabelMapping(BaseModel):
    dataset_key: str
    source_label: str
    label_type: DatasetLabelType
    canonical_taxonomy: Optional[str] = None
    canonical_label: Optional[str] = None
    mapping_status: LabelMappingStatus = LabelMappingStatus.UNMAPPED
    notes: Optional[str] = None


class DatasetQualityReport(BaseModel):
    dataset_key: str
    dataset_name: str
    provider_type: DatasetProviderType
    declared_count: Optional[int] = None
    observed_count: int = 0
    valid_images: int = 0
    invalid_images: int = 0
    exact_duplicate_count: int = 0
    near_duplicate_candidate_count: int = 0
    label_count: int = 0
    unlabeled_count: int = 0
    original_count: int = 0
    augmented_count: int = 0
    synthetic_count: int = 0
    unknown_origin_count: int = 0
    role_distribution: Dict[str, int] = Field(default_factory=dict)
    catalog_eligible_count: int = 0
    historical_candidate_count: int = 0
    quarantine_count: int = 0
    promotion_readiness: str = "INSPECTION_ONLY"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
