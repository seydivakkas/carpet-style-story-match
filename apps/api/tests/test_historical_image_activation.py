"""Unit tests for POST-v1 A8 — Historical Local Image Activation."""
import io
import pytest
from PIL import Image
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.db.models.carpet_historical_connection import HistoricalConnectionResultModel
from app.domain.museum_sources.museum_image_downloader import (
    validate_museum_image_url_host,
    is_museum_host_allowlisted,
    download_museum_image_bytes,
    InvalidHostError,
    InvalidSchemeError,
    ImageOversizeError,
)
from app.domain.images.validation import ImageValidationService
from app.domain.images.exceptions import ImageDecodeFailedError
from app.scripts.activate_museum_sources import run_activation as run_a6_activation
from app.scripts.activate_historical_references import run_activation as run_a7_activation
from app.scripts.activate_historical_images import run_activation as run_a8_activation


def create_synthetic_jpeg_bytes(width: int = 200, height: int = 200, color=(180, 140, 100)) -> bytes:
    """Generate clean synthetic JPEG bytes for offline test execution."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def setup_a6_and_a7(db_session: AsyncSession):
    """Seed test database with A6 museum sources and A7 historical references."""
    await run_a6_activation(provider_filter="all", dry_run=False, apply=True, db_session=db_session)
    await run_a7_activation(dry_run=False, apply=True, db_session=db_session)


@pytest.mark.asyncio
async def test_museum_host_allowlist():
    """Verify that only approved museum hosts are allowlisted."""
    assert is_museum_host_allowlisted("images.metmuseum.org") is True
    assert is_museum_host_allowlisted("framemark.vam.ac.uk") is True
    assert is_museum_host_allowlisted("media.vam.ac.uk") is True
    assert is_museum_host_allowlisted("malicious-domain.com") is False
    assert is_museum_host_allowlisted("fake-metmuseum.org.attacker.com") is False

    validate_museum_image_url_host("https://images.metmuseum.org/CRDImages/ad/original/DP332451.jpg")

    with pytest.raises(InvalidHostError):
        validate_museum_image_url_host("https://evil.com/fake-carpet.jpg")

    with pytest.raises(InvalidSchemeError):
        validate_museum_image_url_host("ftp://images.metmuseum.org/carpet.jpg")


@pytest.mark.asyncio
async def test_open_access_vs_rights_review_gating(db_session: AsyncSession):
    """Verify OPEN_ACCESS_ONLY mode ingests open-access items and gates rights-review items."""
    await setup_a6_and_a7(db_session)

    res_met = await db_session.execute(
        select(HistoricalReferenceMetadataModel).where(
            HistoricalReferenceMetadataModel.open_access.is_(True),
            HistoricalReferenceMetadataModel.source_image_url.isnot(None)
        ).limit(1)
    )
    met_item = res_met.scalar_one_or_none()
    if met_item:
        report_met = await run_a8_activation(
            rights_mode="OPEN_ACCESS_ONLY",
            dry_run=True,
            apply=False,
            reference_key_filter=met_item.reference_key,
            db_session=db_session
        )
        assert report_met["activation_metrics"]["rights_not_eligible"] == 0
        assert report_met["activation_metrics"]["activated"] == 1

    res_vam = await db_session.execute(
        select(HistoricalReferenceMetadataModel).where(
            HistoricalReferenceMetadataModel.reference_key.like("ref-vam-%")
        ).limit(1)
    )
    vam_item = res_vam.scalar_one_or_none()
    if vam_item:
        report_vam = await run_a8_activation(
            rights_mode="OPEN_ACCESS_ONLY",
            dry_run=True,
            apply=False,
            reference_key_filter=vam_item.reference_key,
            db_session=db_session
        )
        assert report_vam["activation_metrics"]["rights_not_eligible"] == 1
        assert report_vam["activation_metrics"]["activated"] == 0


@pytest.mark.asyncio
async def test_invalid_image_bytes_rejection():
    """Verify that non-image bytes (e.g. HTML error page) are rejected by validator."""
    validator = ImageValidationService()
    html_bytes = b"<html><body>404 Not Found</body></html>"
    with pytest.raises(ImageDecodeFailedError):
        validator.validate_and_process_upload(html_bytes, "image/jpeg")


@pytest.mark.asyncio
async def test_oversize_rejection():
    """Verify that downloaded bytes exceeding max limit raise ImageOversizeError."""
    with pytest.raises(ImageOversizeError):
        download_museum_image_bytes(
            "https://images.metmuseum.org/CRDImages/ad/original/DP332451.jpg",
            timeout=5,
            delay_sec=0,
            max_bytes=10
        )


@pytest.mark.asyncio
async def test_idempotency_second_run(db_session: AsyncSession, monkeypatch):
    """Verify second execution skips already active primary images without duplication."""
    await setup_a6_and_a7(db_session)

    synthetic_jpeg = create_synthetic_jpeg_bytes(250, 250)
    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )

    report = await run_a8_activation(
        rights_mode="OPEN_ACCESS_ONLY",
        dry_run=False,
        apply=True,
        db_session=db_session
    )
    total_eligible = report["activation_metrics"]["eligible_for_binary"]
    activated_or_active = report["activation_metrics"]["activated"] + report["activation_metrics"]["already_active"]
    assert activated_or_active == total_eligible
    assert report["activation_metrics"]["unaccounted"] == 0

    # Second run
    report2 = await run_a8_activation(
        rights_mode="OPEN_ACCESS_ONLY",
        dry_run=False,
        apply=True,
        db_session=db_session
    )
    assert report2["activation_metrics"]["activated"] == 0
    assert report2["activation_metrics"]["already_active"] == total_eligible
    assert report2["activation_metrics"]["unaccounted"] == 0


@pytest.mark.asyncio
async def test_readiness_and_boundary_isolation(db_session: AsyncSession, monkeypatch):
    """Verify readiness distribution, zero Style DNA profiles, zero HistoricalConnections, and catalog isolation."""
    await setup_a6_and_a7(db_session)

    synthetic_jpeg = create_synthetic_jpeg_bytes(300, 300)
    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )

    report = await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)
    total_eligible = report["activation_metrics"]["eligible_for_binary"]

    res_hist_img = await db_session.execute(
        select(func.count(CarpetImageModel.id)).join(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
    )
    hist_img_count = res_hist_img.scalar_one()
    assert hist_img_count == total_eligible

    res_cat_carpets = await db_session.execute(
        select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
    )
    cat_carpet_count = res_cat_carpets.scalar_one()
    assert cat_carpet_count in (0, 232)

    res_hist_dna = await db_session.execute(
        select(func.count(CarpetStyleProfileModel.id)).join(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
    )
    assert res_hist_dna.scalar_one() == 0

    res_conn = await db_session.execute(select(func.count(HistoricalConnectionResultModel.id)))
    assert res_conn.scalar_one() == 0
