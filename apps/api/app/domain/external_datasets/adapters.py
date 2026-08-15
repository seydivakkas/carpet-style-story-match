"""Dataset inspection adapters for local directory corpora."""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

from app.domain.external_datasets.classifier import DatasetRoleClassifier
from app.domain.external_datasets.schemas import (
    ManifestRecord,
    DatasetQualityReport,
    DatasetProviderType,
    ImageValidationStatus,
    ExternalDatasetRole,
    CatalogEligibility,
    HistoricalEligibility,
    DatasetLabelType,
)


class LocalDirectoryDatasetAdapter:
    """Adapter for inspecting local directory dataset corpora without database mutations."""

    def __init__(
        self,
        dataset_key: str,
        input_dir: Path,
        provider_type: DatasetProviderType,
        source_url: str = "",
        license_name: str = "Unknown",
        license_verified: bool = False,
        manufacturer: Optional[str] = None,
        institution: Optional[str] = None,
    ):
        self.dataset_key = dataset_key
        self.input_dir = Path(input_dir)
        self.provider_type = provider_type
        self.source_url = source_url
        self.license_name = license_name
        self.license_verified = license_verified
        self.manufacturer = manufacturer
        self.institution = institution

    def inspect_and_build_manifest(self) -> Tuple[List[ManifestRecord], DatasetQualityReport]:
        records: List[ManifestRecord] = []
        role_dist: Dict[str, int] = {role.value: 0 for role in ExternalDatasetRole}
        sha_counts: Dict[str, int] = {}

        valid_images = 0
        invalid_images = 0
        original_count = 0
        augmented_count = 0
        synthetic_count = 0
        unknown_origin_count = 0
        labeled_count = 0
        unlabeled_count = 0

        catalog_eligible_count = 0
        historical_candidate_count = 0
        quarantine_count = 0

        # Scan files
        if self.input_dir.exists():
            for root, _, files in os.walk(self.input_dir):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                        continue

                    full_path = Path(root) / f
                    rel_path = str(full_path.relative_to(self.input_dir)).replace("\\", "/")

                    # SHA-256 hash
                    try:
                        hasher = hashlib.sha256()
                        with open(full_path, "rb") as fh:
                            while chunk := fh.read(8192):
                                hasher.update(chunk)
                        sha256 = hasher.hexdigest()
                    except Exception:
                        sha256 = "UNKNOWN_CORRUPT"

                    sha_counts[sha256] = sha_counts.get(sha256, 0) + 1

                    # Image validation check
                    img_status = ImageValidationStatus.VALID
                    w, h = None, None
                    try:
                        with Image.open(full_path) as img:
                            img.verify()
                        with Image.open(full_path) as img:
                            w, h = img.size
                            if w < 10 or h < 10 or w > 10000 or h > 10000:
                                img_status = ImageValidationStatus.INVALID_IMAGE
                    except Exception:
                        img_status = ImageValidationStatus.INVALID_IMAGE

                    if img_status == ImageValidationStatus.VALID:
                        valid_images += 1
                    else:
                        invalid_images += 1

                    # Path conventions for metadata heuristics
                    lower_rel = rel_path.lower()
                    is_synthetic = "synthetic" in lower_rel or "generated" in lower_rel
                    is_augmented = "augmented" in lower_rel or "aug" in lower_rel or "flipped" in lower_rel
                    is_original = not (is_synthetic or is_augmented)

                    if is_synthetic:
                        synthetic_count += 1
                    elif is_augmented:
                        augmented_count += 1
                    elif is_original:
                        original_count += 1
                    else:
                        unknown_origin_count += 1

                    # Source label from folder or filename
                    parts = rel_path.split("/")
                    source_label = None
                    if len(parts) > 1:
                        source_label = parts[0]
                        labeled_count += 1
                    else:
                        unlabeled_count += 1

                    namespaced_label = f"{self.dataset_key}:{source_label}" if source_label else None

                    # Extract SKU / Object ID if present in metadata/filename
                    official_sku = None
                    original_object_id = None

                    if self.provider_type == DatasetProviderType.OFFICIAL_MANUFACTURER:
                        # Extract official SKU from filename if formatted as SKU (e.g., MERINOS_12345_060)
                        stem = Path(f).stem
                        if " " in stem or "_" in stem:
                            official_sku = stem.replace("_", " ").strip()
                        else:
                            official_sku = stem.strip()
                    elif self.provider_type in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE):
                        stem = Path(f).stem
                        original_object_id = stem.strip()

                    rec_id = f"{self.dataset_key}:{sha256[:16]}"

                    # Classify role
                    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
                        provider_type=self.provider_type,
                        manufacturer=self.manufacturer,
                        official_sku=official_sku,
                        official_product_url=self.source_url if self.provider_type == DatasetProviderType.OFFICIAL_MANUFACTURER else None,
                        institution=self.institution,
                        original_object_id=original_object_id,
                        original_source_url=self.source_url if self.provider_type in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE) else None,
                        license_verified=self.license_verified,
                        is_original=is_original,
                        is_augmented=is_augmented,
                        is_synthetic=is_synthetic,
                    )

                    role_dist[role.value] = role_dist.get(role.value, 0) + 1

                    if cat_elig == CatalogEligibility.ELIGIBLE:
                        catalog_eligible_count += 1
                    if hist_elig == HistoricalEligibility.ELIGIBLE:
                        historical_candidate_count += 1
                    if role == ExternalDatasetRole.QUARANTINE:
                        quarantine_count += 1

                    rec = ManifestRecord(
                        record_id=rec_id,
                        dataset_key=self.dataset_key,
                        relative_image_path=rel_path,
                        content_sha256=sha256,
                        original_source_url=self.source_url or None,
                        original_object_id=original_object_id,
                        source_label=source_label,
                        namespaced_label=namespaced_label,
                        is_original=is_original,
                        is_augmented=is_augmented,
                        is_synthetic=is_synthetic,
                        license_name=self.license_name,
                        license_verified=self.license_verified,
                        classified_role=role,
                        catalog_eligibility=cat_elig,
                        historical_eligibility=hist_elig,
                        classification_reasons=reasons,
                        image_validation_status=img_status,
                        manufacturer=self.manufacturer,
                        official_sku=official_sku,
                        institution=self.institution,
                        image_width=w,
                        image_height=h,
                    )
                    records.append(rec)

        # Count exact duplicates
        exact_dup_count = sum(cnt - 1 for cnt in sha_counts.values() if cnt > 1)

        readiness = "INSPECTION_ONLY"
        if catalog_eligible_count > 0:
            readiness = "CATALOG_PROMOTION_READY"
        elif historical_candidate_count > 0:
            readiness = "HISTORICAL_REVIEW_READY"

        report = DatasetQualityReport(
            dataset_key=self.dataset_key,
            dataset_name=self.dataset_key.replace("-", " ").title(),
            provider_type=self.provider_type,
            declared_count=len(records),
            observed_count=len(records),
            valid_images=valid_images,
            invalid_images=invalid_images,
            exact_duplicate_count=exact_dup_count,
            near_duplicate_candidate_count=0,
            label_count=labeled_count,
            unlabeled_count=unlabeled_count,
            original_count=original_count,
            augmented_count=augmented_count,
            synthetic_count=synthetic_count,
            unknown_origin_count=unknown_origin_count,
            role_distribution=role_dist,
            catalog_eligible_count=catalog_eligible_count,
            historical_candidate_count=historical_candidate_count,
            quarantine_count=quarantine_count,
            promotion_readiness=readiness,
        )

        return records, report
