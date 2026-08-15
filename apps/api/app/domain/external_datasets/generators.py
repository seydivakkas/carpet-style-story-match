"""Candidate payload generators for eligible external dataset records."""
from typing import List, Dict, Any
from app.domain.external_datasets.schemas import (
    ManifestRecord,
    ExternalDatasetRole,
    CatalogEligibility,
    HistoricalEligibility,
)


def generate_catalog_candidates(records: List[ManifestRecord]) -> List[Dict[str, Any]]:
    """Generate carpet-catalog-curation-v1 compatible payloads for eligible catalog candidates only."""
    candidates: List[Dict[str, Any]] = []

    for r in records:
        # Strict gate
        if r.classified_role != ExternalDatasetRole.CATALOG_CANDIDATE:
            continue
        if r.catalog_eligibility != CatalogEligibility.ELIGIBLE:
            continue
        if not r.license_verified:
            continue
        if not r.official_sku or not r.official_sku.strip():
            continue
        if not r.manufacturer or not r.manufacturer.strip():
            continue

        item = {
            "sku": r.official_sku,
            "title": f"{r.manufacturer} {r.official_sku}",
            "brand": r.manufacturer,
            "collection": r.source_label or "Default Collection",
            "source_url": r.original_source_url,
            "image_path": r.relative_image_path,
            "content_sha256": r.content_sha256,
            "license_name": r.license_name,
            "dataset_key": r.dataset_key,
        }
        candidates.append(item)

    return candidates


def generate_historical_candidates(records: List[ManifestRecord]) -> List[Dict[str, Any]]:
    """Generate historical candidate review payloads for eligible historical records only."""
    candidates: List[Dict[str, Any]] = []

    for r in records:
        # Strict gate
        if r.classified_role != ExternalDatasetRole.HISTORICAL_CANDIDATE:
            continue
        if r.historical_eligibility != HistoricalEligibility.ELIGIBLE:
            continue
        if not r.institution or not r.institution.strip():
            continue
        if not r.original_object_id or not r.original_object_id.strip():
            continue
        if not r.original_source_url or not r.original_source_url.strip():
            continue

        item = {
            "institution": r.institution,
            "object_id": r.original_object_id,
            "source_url": r.original_source_url,
            "image_path": r.relative_image_path,
            "content_sha256": r.content_sha256,
            "source_label": r.source_label,
            "namespaced_label": r.namespaced_label,
            "dataset_key": r.dataset_key,
            "review_status": "PENDING_CURATION_REVIEW",
        }
        candidates.append(item)

    return candidates
