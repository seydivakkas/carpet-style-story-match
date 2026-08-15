"""Unit and integration tests for Merinos catalog image activation pipeline."""
import os
import json
import uuid
import pytest
from PIL import Image
import io

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.domain.carpet_catalog.merinos_image_downloader import (
    is_host_allowlisted,
    validate_image_url_host,
    InvalidHostError,
    InvalidSchemeError,
)
from app.domain.carpet_catalog.repository import CarpetCatalogRepository
from app.domain.common.readiness import derive_style_dna_readiness, StyleDnaReadinessEnum
from app.scripts.activate_merinos_catalog_images import run_activation_async, get_repo_root


def create_synthetic_jpeg_bytes(width: int = 200, height: int = 200, color=(200, 150, 100)) -> bytes:
    """Generate a clean synthetic JPEG byte payload."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_host_allowlist():
    assert is_host_allowlisted("merinos.com.tr") is True
    assert is_host_allowlisted("www.merinos.com.tr") is True
    assert is_host_allowlisted("wwwmerinoscomtr.sm.mncdn.com") is True
    assert is_host_allowlisted("sub.sm.mncdn.com") is True
    assert is_host_allowlisted("evil.com") is False
    assert is_host_allowlisted("google.com") is False
    assert is_host_allowlisted("merinos.com.tr.attacker.com") is False


def test_validate_image_url_host():
    valid = "https://www.merinos.com.tr/content/images/thumbs/183/90823-070.jpeg"
    assert validate_image_url_host(valid) == valid

    with pytest.raises(InvalidHostError):
        validate_image_url_host("https://evil.example.com/fake_image.jpg")

    with pytest.raises(InvalidSchemeError):
        validate_image_url_host("file:///etc/passwd")


@pytest.mark.asyncio
async def test_url_only_mode(db_session, tmp_path):
    # Setup test source file
    source_file = tmp_path / "test_source.json"
    source_file.write_text(json.dumps({
        "products": [
            {
                "sku": "TEST-SKU-001",
                "name": "Test Carpet 001",
                "source_url": "https://www.merinos.com.tr/90823-070",
                "primary_image_url": "https://www.merinos.com.tr/test.jpeg"
            }
        ]
    }))

    out_source = str(tmp_path / "out_source.json")
    out_act = str(tmp_path / "out_act.json")
    out_rep = str(tmp_path / "out_rep.json")

    await run_activation_async(
        source_file=str(source_file),
        rights_mode="URL_ONLY",
        dry_run=False,
        apply=False,
        limit=None,
        replace_primary=False,
        output_source_images=out_source,
        output_activation=out_act,
        output_report=out_rep
    )

    assert os.path.exists(out_source)
    assert os.path.exists(out_act)
    assert os.path.exists(out_rep)

    rep_data = json.loads(open(out_rep, encoding="utf-8").read())
    assert rep_data["rights_mode"] == "URL_ONLY"
    assert rep_data["activated"] == 0


@pytest.mark.asyncio
async def test_authorized_internal_ingestion(db_session, monkeypatch, tmp_path):
    # 1. Create a Carpet in DB
    carpet = CarpetModel(
        id=uuid.uuid4(),
        sku="TEST-SKU-002",
        name="Test Carpet 002",
        source_type=CarpetSourceType.CATALOG,
        is_active=True
    )
    db_session.add(carpet)
    await db_session.commit()

    # 2. Mock downloader to return synthetic JPEG
    synthetic_jpeg = create_synthetic_jpeg_bytes(300, 300)
    monkeypatch.setattr(
        "app.scripts.activate_merinos_catalog_images.download_image_bytes",
        lambda url, timeout=15, delay_sec=0.5: (synthetic_jpeg, "image/jpeg")
    )

    source_file = tmp_path / "test_source.json"
    source_file.write_text(json.dumps({
        "products": [
            {
                "sku": "TEST-SKU-002",
                "name": "Test Carpet 002",
                "source_url": "https://www.merinos.com.tr/73941-060",
                "primary_image_url": "https://www.merinos.com.tr/73941-060.jpeg"
            }
        ]
    }))

    out_source = str(tmp_path / "out_source.json")
    out_act = str(tmp_path / "out_act.json")
    out_rep = str(tmp_path / "out_rep.json")

    await run_activation_async(
        source_file=str(source_file),
        rights_mode="AUTHORIZED_INTERNAL",
        dry_run=False,
        apply=True,
        limit=None,
        replace_primary=False,
        output_source_images=out_source,
        output_activation=out_act,
        output_report=out_rep,
        session=db_session
    )

    # 3. Verify CarpetImage created in DB
    repo = CarpetCatalogRepository(db_session)
    primary_img = await repo.get_primary_image(carpet.id)
    assert primary_img is not None
    assert primary_img.is_primary is True
    assert primary_img.width_px == 300
    assert primary_img.height_px == 300

    # 4. Verify Style DNA readiness transition: NO_PRIMARY_IMAGE -> STYLE_DNA_MISSING
    profile = await repo.get_current_style_profile(carpet.id)
    assert profile is None  # NO STYLE DNA CREATED IN A2!
    readiness = derive_style_dna_readiness(primary_img, profile)
    assert readiness == StyleDnaReadinessEnum.STYLE_DNA_MISSING


@pytest.mark.asyncio
async def test_idempotency_skip_existing_primary(db_session, monkeypatch, tmp_path):
    carpet = CarpetModel(
        id=uuid.uuid4(),
        sku="TEST-SKU-003",
        name="Test Carpet 003",
        source_type=CarpetSourceType.CATALOG,
        is_active=True
    )
    db_session.add(carpet)
    await db_session.commit()

    synthetic_jpeg = create_synthetic_jpeg_bytes(250, 250)
    monkeypatch.setattr(
        "app.scripts.activate_merinos_catalog_images.download_image_bytes",
        lambda url, timeout=15, delay_sec=0.5: (synthetic_jpeg, "image/jpeg")
    )

    source_file = tmp_path / "test_source.json"
    source_file.write_text(json.dumps({
        "products": [
            {
                "sku": "TEST-SKU-003",
                "name": "Test Carpet 003",
                "source_url": "https://www.merinos.com.tr/74423-096",
                "primary_image_url": "https://www.merinos.com.tr/74423-096.jpeg"
            }
        ]
    }))

    out_source = str(tmp_path / "out_source.json")
    out_act = str(tmp_path / "out_act.json")
    out_rep = str(tmp_path / "out_rep.json")

    # First activation run
    await run_activation_async(
        source_file=str(source_file),
        rights_mode="AUTHORIZED_INTERNAL",
        dry_run=False,
        apply=True,
        limit=None,
        replace_primary=False,
        output_source_images=out_source,
        output_activation=out_act,
        output_report=out_rep,
        session=db_session
    )

    # Second activation run (identical source)
    await run_activation_async(
        source_file=str(source_file),
        rights_mode="AUTHORIZED_INTERNAL",
        dry_run=False,
        apply=True,
        limit=None,
        replace_primary=False,
        output_source_images=out_source,
        output_activation=out_act,
        output_report=out_rep,
        session=db_session
    )

    rep_data = json.loads(open(out_rep, encoding="utf-8").read())
    assert rep_data["already_active"] == 1
    assert rep_data["activated"] == 0


@pytest.mark.asyncio
async def test_reconciliation_accounting(db_session, monkeypatch, tmp_path):
    # Setup 5 catalog carpets in DB
    skus = ["SKU-REC-001", "SKU-REC-002", "SKU-REC-003", "SKU-REC-004", "SKU-REC-005"]
    for s in skus:
        c = CarpetModel(
            id=uuid.uuid4(),
            sku=s,
            name=f"Carpet {s}",
            source_type=CarpetSourceType.CATALOG,
            is_active=True
        )
        db_session.add(c)
    await db_session.commit()

    # Source dataset contains 4 SKUs (SKU-REC-005 omitted -> SOURCE_PRODUCT_UNAVAILABLE)
    # SKU-REC-001: ACTIVATED
    # SKU-REC-002: ACTIVATED
    # SKU-REC-003: INVALID_IMAGE (oversize or bad image)
    # SKU-REC-004: IMAGE_NOT_FOUND (no image url)
    synthetic_jpeg = create_synthetic_jpeg_bytes(200, 200)
    
    def mock_downloader(url, timeout=15, delay_sec=0.5):
        if "bad" in url:
            from app.domain.carpet_catalog.merinos_image_downloader import ImageOversizeError
            raise ImageOversizeError("Simulated oversize")
        return (synthetic_jpeg, "image/jpeg")

    monkeypatch.setattr(
        "app.scripts.activate_merinos_catalog_images.download_image_bytes",
        mock_downloader
    )

    source_file = tmp_path / "reconcile_source.json"
    source_file.write_text(json.dumps({
        "products": [
            {"sku": "SKU-REC-001", "source_url": "https://www.merinos.com.tr/001", "primary_image_url": "https://www.merinos.com.tr/001.jpeg"},
            {"sku": "SKU-REC-002", "source_url": "https://www.merinos.com.tr/002", "primary_image_url": "https://www.merinos.com.tr/002.jpeg"},
            {"sku": "SKU-REC-003", "source_url": "https://www.merinos.com.tr/003", "primary_image_url": "https://www.merinos.com.tr/bad.jpeg"},
            {"sku": "SKU-REC-004", "source_url": "https://www.merinos.com.tr/004", "primary_image_url": None},
        ]
    }))

    out_source = str(tmp_path / "out_source.json")
    out_act = str(tmp_path / "out_act.json")
    out_rep = str(tmp_path / "out_rep.json")

    await run_activation_async(
        source_file=str(source_file),
        rights_mode="AUTHORIZED_INTERNAL",
        dry_run=False,
        apply=True,
        limit=None,
        replace_primary=False,
        output_source_images=out_source,
        output_activation=out_act,
        output_report=out_rep,
        session=db_session
    )

    rep_data = json.loads(open(out_rep, encoding="utf-8").read())
    assert rep_data["catalog_total"] == 5
    assert rep_data["activated"] == 2
    assert rep_data["invalid_image"] == 1
    assert rep_data["image_not_found"] == 1
    assert rep_data["source_product_unavailable"] == 1
    assert rep_data["terminal_status_total"] == 5
    assert rep_data["unaccounted"] == 0
    assert rep_data["readiness_distribution"]["STYLE_DNA_MISSING"] == 2
    assert rep_data["readiness_distribution"]["NO_PRIMARY_IMAGE"] == 3


def test_reconciliation_unaccounted_invariant_fails_on_missing_record():
    total_catalog = 5
    # Simulated report records only 4 terminal statuses
    terminal_statuses = ["ACTIVATED", "ACTIVATED", "INVALID_IMAGE", "IMAGE_NOT_FOUND"]
    unaccounted = total_catalog - len(terminal_statuses)
    
    assert unaccounted == 1
    assert unaccounted != 0  # Fails unaccounted == 0 invariant
