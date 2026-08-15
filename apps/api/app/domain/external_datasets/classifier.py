"""Deterministic DatasetRoleClassifier for classifying external carpet dataset records."""
from typing import List, Tuple, Optional
from app.domain.external_datasets.schemas import (
    ExternalDatasetRole,
    CatalogEligibility,
    HistoricalEligibility,
    DatasetProviderType,
)


class DatasetRoleClassifier:
    """Pure deterministic role classifier. Zero black-box pixel or label guesswork."""

    @staticmethod
    def classify(
        provider_type: DatasetProviderType,
        authoritative_source_type: Optional[DatasetProviderType] = None,
        manufacturer: Optional[str] = None,
        official_sku: Optional[str] = None,
        official_product_url: Optional[str] = None,
        institution: Optional[str] = None,
        original_object_id: Optional[str] = None,
        original_source_url: Optional[str] = None,
        license_verified: bool = False,
        is_original: bool = True,
        is_augmented: bool = False,
        is_synthetic: bool = False,
    ) -> Tuple[ExternalDatasetRole, CatalogEligibility, HistoricalEligibility, List[str]]:
        reasons: List[str] = []

        # Default init
        role: ExternalDatasetRole = ExternalDatasetRole.QUARANTINE
        cat_elig: CatalogEligibility = CatalogEligibility.INELIGIBLE
        hist_elig: HistoricalEligibility = HistoricalEligibility.INELIGIBLE

        effective_auth_source = authoritative_source_type or provider_type

        # 1. Check synthetic or augmented invariant
        if is_synthetic:
            reasons.append("synthetic_image_detected")
            role = ExternalDatasetRole.BENCHMARK_ONLY
            cat_elig = CatalogEligibility.INELIGIBLE
            hist_elig = HistoricalEligibility.INELIGIBLE
            return role, cat_elig, hist_elig, reasons

        if is_augmented:
            reasons.append("augmented_image_detected")
            role = ExternalDatasetRole.BENCHMARK_ONLY
            cat_elig = CatalogEligibility.INELIGIBLE
            hist_elig = HistoricalEligibility.INELIGIBLE
            return role, cat_elig, hist_elig, reasons

        # 2. Check catalog candidate criteria
        is_official_provider = provider_type == DatasetProviderType.OFFICIAL_MANUFACTURER
        has_manufacturer = bool(manufacturer and manufacturer.strip())
        has_sku = bool(official_sku and official_sku.strip())
        has_product_url = bool(
            (official_product_url and official_product_url.strip())
            or (original_source_url and original_source_url.strip())
        )

        if is_official_provider:
            if not has_manufacturer:
                reasons.append("missing_official_manufacturer")
            if not has_sku:
                reasons.append("missing_official_product_sku")
            if not has_product_url:
                reasons.append("missing_official_product_url")
            if not license_verified:
                reasons.append("unverified_license_rights")

            if has_manufacturer and has_sku and has_product_url:
                if license_verified:
                    reasons.append("official_manufacturer_provenance_verified")
                    role = ExternalDatasetRole.CATALOG_CANDIDATE
                    cat_elig = CatalogEligibility.ELIGIBLE
                    hist_elig = HistoricalEligibility.INELIGIBLE
                    return role, cat_elig, hist_elig, reasons
                else:
                    reasons.append("license_unverified_requires_review")
                    role = ExternalDatasetRole.CATALOG_CANDIDATE
                    cat_elig = CatalogEligibility.REVIEW_REQUIRED
                    hist_elig = HistoricalEligibility.INELIGIBLE
                    return role, cat_elig, hist_elig, reasons
            else:
                role = ExternalDatasetRole.QUARANTINE
                cat_elig = CatalogEligibility.INELIGIBLE
                hist_elig = HistoricalEligibility.INELIGIBLE
                return role, cat_elig, hist_elig, reasons

        # 3. Check object-level historical candidate criteria
        has_institution = bool(institution and institution.strip())
        has_object_id = bool(original_object_id and original_object_id.strip())
        has_source_url = bool(original_source_url and original_source_url.strip())

        is_museum_or_archive = (
            provider_type in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE)
            or effective_auth_source in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE)
            or (has_institution and has_object_id and has_source_url)
        )

        if is_museum_or_archive and is_original:
            if has_institution and has_object_id and has_source_url:
                if provider_type in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE):
                    reasons.append("institutional_historical_provenance_verified")
                else:
                    reasons.append("secondary_dataset_with_verified_institutional_provenance")
                role = ExternalDatasetRole.HISTORICAL_CANDIDATE
                cat_elig = CatalogEligibility.INELIGIBLE
                hist_elig = HistoricalEligibility.ELIGIBLE
                return role, cat_elig, hist_elig, reasons
            elif provider_type in (DatasetProviderType.MUSEUM, DatasetProviderType.ARCHIVE):
                if not has_institution:
                    reasons.append("missing_institution_identity")
                if not has_object_id:
                    reasons.append("missing_institutional_object_id")
                if not has_source_url:
                    reasons.append("missing_original_source_url")
                reasons.append("incomplete_historical_metadata_requires_review")
                role = ExternalDatasetRole.HISTORICAL_CANDIDATE
                cat_elig = CatalogEligibility.INELIGIBLE
                hist_elig = HistoricalEligibility.REVIEW_REQUIRED
                return role, cat_elig, hist_elig, reasons

        # 4. Research dataset providers without object-level museum provenance
        if provider_type in (
            DatasetProviderType.KAGGLE,
            DatasetProviderType.ROBOFLOW,
            DatasetProviderType.ACADEMIC_DATASET,
            DatasetProviderType.GITHUB,
            DatasetProviderType.INTERNAL,
            DatasetProviderType.OTHER,
        ):
            reasons.append(f"research_dataset_source_{provider_type.value.lower()}")
            if not has_sku:
                reasons.append("missing_official_product_sku")
            if not (has_institution and has_object_id):
                reasons.append("missing_object_level_historical_provenance")
            role = ExternalDatasetRole.RESEARCH_ONLY
            cat_elig = CatalogEligibility.INELIGIBLE
            hist_elig = HistoricalEligibility.INELIGIBLE
            return role, cat_elig, hist_elig, reasons

        # 5. Quarantine fallback
        reasons.append("unknown_or_untrusted_provenance")
        role = ExternalDatasetRole.QUARANTINE
        cat_elig = CatalogEligibility.INELIGIBLE
        hist_elig = HistoricalEligibility.INELIGIBLE
        return role, cat_elig, hist_elig, reasons
