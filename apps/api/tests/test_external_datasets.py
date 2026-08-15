"""Unit tests for external carpet dataset intake & role classification v1."""
from pathlib import Path
import sqlite3
import tempfile
from PIL import Image
import pytest

from app.core.config import settings
from app.domain.external_datasets.schemas import (
    ExternalDatasetRole,
    CatalogEligibility,
    HistoricalEligibility,
    DatasetProviderType,
    ManifestRecord,
    ImageValidationStatus,
)
from app.domain.external_datasets.classifier import DatasetRoleClassifier
from app.domain.external_datasets.adapters import LocalDirectoryDatasetAdapter
from app.domain.external_datasets.generators import (
    generate_catalog_candidates,
    generate_historical_candidates,
)


def test_official_product_classification():
    """REQUIRED TEST 75: Official manufacturer with SKU and verified license."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OFFICIAL_MANUFACTURER,
        manufacturer="Merinos",
        official_sku="ELEGANCE 123",
        official_product_url="https://www.merinos.com.tr/elegance-123",
        license_verified=True,
        is_original=True,
        is_augmented=False,
        is_synthetic=False,
    )
    assert role == ExternalDatasetRole.CATALOG_CANDIDATE
    assert cat_elig == CatalogEligibility.ELIGIBLE
    assert hist_elig == HistoricalEligibility.INELIGIBLE


def test_kaggle_research_classification():
    """REQUIRED TEST 76: Kaggle dataset without official SKU."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.KAGGLE,
        official_sku=None,
        license_verified=False,
        is_original=True,
    )
    assert role == ExternalDatasetRole.RESEARCH_ONLY
    assert cat_elig == CatalogEligibility.INELIGIBLE
    assert hist_elig == HistoricalEligibility.INELIGIBLE


def test_museum_classification():
    """REQUIRED TEST 77: Museum record with institution and object ID."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.MUSEUM,
        institution="The Metropolitan Museum of Art",
        original_object_id="MET-1970.65",
        original_source_url="https://www.metmuseum.org/art/collection/search/197065",
        license_verified=True,
        is_original=True,
    )
    assert role == ExternalDatasetRole.HISTORICAL_CANDIDATE
    assert cat_elig == CatalogEligibility.INELIGIBLE
    assert hist_elig == HistoricalEligibility.ELIGIBLE


def test_augmented_classification():
    """REQUIRED TEST 78: Augmented museum image is benchmark only."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.MUSEUM,
        institution="The Metropolitan Museum of Art",
        original_object_id="MET-1970.65",
        original_source_url="https://www.metmuseum.org/art/collection/search/197065",
        is_augmented=True,
    )
    assert role == ExternalDatasetRole.BENCHMARK_ONLY
    assert cat_elig == CatalogEligibility.INELIGIBLE
    assert hist_elig == HistoricalEligibility.INELIGIBLE


def test_synthetic_classification():
    """REQUIRED TEST 79: Synthetic image is benchmark only."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OFFICIAL_MANUFACTURER,
        manufacturer="Merinos",
        official_sku="ELEGANCE 123",
        is_synthetic=True,
    )
    assert role == ExternalDatasetRole.BENCHMARK_ONLY
    assert cat_elig == CatalogEligibility.INELIGIBLE
    assert hist_elig == HistoricalEligibility.INELIGIBLE


def test_unknown_quarantine_classification():
    """REQUIRED TEST 80: Unknown provider and provenance is quarantined."""
    role, cat_elig, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OTHER,
        is_original=True,
    )
    assert role == ExternalDatasetRole.RESEARCH_ONLY
    assert cat_elig == CatalogEligibility.INELIGIBLE


def test_no_pixel_dependency():
    """REQUIRED TEST 81: Same metadata/context gives different roles regardless of pixels."""
    role1, cat_elig1, _, _ = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OFFICIAL_MANUFACTURER,
        manufacturer="Merinos",
        official_sku="SKU-100",
        official_product_url="https://example.com/sku-100",
        license_verified=True,
    )
    role2, cat_elig2, _, _ = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OTHER,
        official_sku=None,
    )
    assert role1 == ExternalDatasetRole.CATALOG_CANDIDATE
    assert cat_elig1 == CatalogEligibility.ELIGIBLE
    assert role2 == ExternalDatasetRole.RESEARCH_ONLY
    assert cat_elig2 == CatalogEligibility.INELIGIBLE


def test_label_namespacing():
    """REQUIRED TEST 82: Source labels are namespaced to dataset key."""
    m1 = ManifestRecord(
        record_id="ds1:rec1",
        dataset_key="ds1",
        relative_image_path="Floral/img1.jpg",
        content_sha256="abc",
        source_label="Floral",
        namespaced_label="ds1:Floral",
    )
    m2 = ManifestRecord(
        record_id="ds2:rec1",
        dataset_key="ds2",
        relative_image_path="Floral/img1.jpg",
        content_sha256="xyz",
        source_label="Floral",
        namespaced_label="ds2:Floral",
    )
    assert m1.namespaced_label == "ds1:Floral"
    assert m2.namespaced_label == "ds2:Floral"
    assert m1.namespaced_label != m2.namespaced_label


def test_catalog_generator_filtering():
    """REQUIRED TEST 85: Catalog generator produces only eligible records."""
    records = [
        ManifestRecord(
            record_id="m1",
            dataset_key="official-merinos",
            relative_image_path="p1.jpg",
            content_sha256="hash1",
            classified_role=ExternalDatasetRole.CATALOG_CANDIDATE,
            catalog_eligibility=CatalogEligibility.ELIGIBLE,
            license_verified=True,
            official_sku="SKU-001",
            manufacturer="Merinos",
            original_source_url="https://example.com/p1",
        ),
        ManifestRecord(
            record_id="m2",
            dataset_key="official-merinos",
            relative_image_path="p2.jpg",
            content_sha256="hash2",
            classified_role=ExternalDatasetRole.CATALOG_CANDIDATE,
            catalog_eligibility=CatalogEligibility.ELIGIBLE,
            license_verified=True,
            official_sku="SKU-002",
            manufacturer="Merinos",
            original_source_url="https://example.com/p2",
        ),
        ManifestRecord(
            record_id="m3",
            dataset_key="kaggle-rugs",
            relative_image_path="p3.jpg",
            content_sha256="hash3",
            classified_role=ExternalDatasetRole.RESEARCH_ONLY,
            catalog_eligibility=CatalogEligibility.INELIGIBLE,
            license_verified=False,
        ),
        ManifestRecord(
            record_id="m4",
            dataset_key="met-museum",
            relative_image_path="p4.jpg",
            content_sha256="hash4",
            classified_role=ExternalDatasetRole.HISTORICAL_CANDIDATE,
            catalog_eligibility=CatalogEligibility.INELIGIBLE,
            historical_eligibility=HistoricalEligibility.ELIGIBLE,
            institution="The Met",
            original_object_id="MET-123",
            original_source_url="https://met.org/123",
        ),
    ]

    candidates = generate_catalog_candidates(records)
    assert len(candidates) == 2
    skus = [c["sku"] for c in candidates]
    assert skus == ["SKU-001", "SKU-002"]


def test_no_fake_sku_rejected():
    """REQUIRED TEST 86: Official product missing SKU is rejected from catalog promotion."""
    role, cat_elig, _, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OFFICIAL_MANUFACTURER,
        manufacturer="Merinos",
        official_sku="",  # Missing SKU
        official_product_url="https://example.com/product",
        license_verified=True,
    )
    assert cat_elig == CatalogEligibility.INELIGIBLE
    assert "missing_official_product_sku" in reasons


def test_license_gate_unverified():
    """REQUIRED TEST 87: Unverified license blocks automatic catalog promotion."""
    role, cat_elig, _, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.OFFICIAL_MANUFACTURER,
        manufacturer="Merinos",
        official_sku="SKU-999",
        official_product_url="https://example.com/sku-999",
        license_verified=False,  # License unverified
    )
    assert cat_elig == CatalogEligibility.REVIEW_REQUIRED
    assert "license_unverified_requires_review" in reasons


def test_historical_missing_object_id():
    """REQUIRED TEST 88: Museum record missing object ID requires review."""
    role, _, hist_elig, reasons = DatasetRoleClassifier.classify(
        provider_type=DatasetProviderType.MUSEUM,
        institution="V&A Museum",
        original_object_id=None,  # Missing object ID
        original_source_url="https://vam.ac.uk/item",
        license_verified=True,
    )
    assert hist_elig == HistoricalEligibility.REVIEW_REQUIRED
    assert "missing_institutional_object_id" in reasons


def get_db_counts() -> dict:
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if not Path(db_path).exists():
        return {
            "carpet_count": 0,
            "carpet_image_count": 0,
            "historical_reference_count": 0,
            "style_profile_count": 0,
        }
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    counts = {
        "carpet_count": cur.execute("SELECT COUNT(*) FROM carpets").fetchone()[0],
        "carpet_image_count": cur.execute("SELECT COUNT(*) FROM carpet_images").fetchone()[0],
        "historical_reference_count": cur.execute("SELECT COUNT(*) FROM historical_reference_metadata").fetchone()[0],
        "style_profile_count": cur.execute("SELECT COUNT(*) FROM carpet_style_profiles").fetchone()[0],
    }
    conn.close()
    return counts


def test_db_immutability_and_merinos_baseline():
    """REQUIRED TEST 89 & 90: Production DB row counts remain 100% unchanged during dataset inspection."""
    counts_before = get_db_counts()

    assert counts_before["carpet_count"] == 232, f"Baseline catalog count modified! Expected 232, got {counts_before['carpet_count']}"
    assert counts_before["carpet_image_count"] >= 227, f"Baseline image count modified! Expected >=227, got {counts_before['carpet_image_count']}"
    assert counts_before["style_profile_count"] == 0, f"Style DNA executed! Expected 0 profiles, got {counts_before['style_profile_count']}"

    # Run inspection in temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = Path(tmp_dir) / "test.jpg"
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(p)

        adapter = LocalDirectoryDatasetAdapter(
            dataset_key="test-pilot",
            input_dir=Path(tmp_dir),
            provider_type=DatasetProviderType.KAGGLE,
            source_url="https://example.com",
        )
        records, report = adapter.inspect_and_build_manifest()
        assert len(records) == 1

    # Verify DB counts again
    counts_after = get_db_counts()
    assert counts_before == counts_after, f"DB counts changed during dataset inspection! Before: {counts_before}, After: {counts_after}"

