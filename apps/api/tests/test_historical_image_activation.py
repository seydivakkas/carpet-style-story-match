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
    """Seed test database with full 100 A7 historical references."""
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


@pytest.mark.asyncio
async def test_rights_baseline_derived_only_from_metadata(db_session: AsyncSession):
    """Verify eligibility comes strictly from open_access/CC0 metadata and NOT provider-name shortcuts."""
    res = await db_session.execute(select(HistoricalReferenceMetadataModel))
    metas = res.scalars().all()
    if not metas:
        await setup_a6_and_a7(db_session)
        res = await db_session.execute(select(HistoricalReferenceMetadataModel))
        metas = res.scalars().all()

    expected_eligible = sum(1 for m in metas if (m.open_access is True or (m.rights_statement and "CC0" in m.rights_statement)))
    expected_ineligible = len(metas) - expected_eligible

    report = await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=True, apply=False, db_session=db_session)
    assert report["activation_metrics"]["eligible_for_binary"] == expected_eligible
    assert report["activation_metrics"]["rights_not_eligible"] == expected_ineligible


@pytest.mark.asyncio
async def test_met_restricted_records_gated(db_session: AsyncSession):
    """Verify the non-open-access Met records evaluate to RIGHTS_NOT_ELIGIBLE."""
    res = await db_session.execute(
        select(HistoricalReferenceMetadataModel).where(
            HistoricalReferenceMetadataModel.reference_key.like("ref-met-%"),
            HistoricalReferenceMetadataModel.open_access.is_(False)
        )
    )
    non_oa_met = res.scalars().all()
    if not non_oa_met:
        await setup_a6_and_a7(db_session)
        res = await db_session.execute(
            select(HistoricalReferenceMetadataModel).where(
                HistoricalReferenceMetadataModel.reference_key.like("ref-met-%"),
                HistoricalReferenceMetadataModel.open_access.is_(False)
            )
        )
        non_oa_met = res.scalars().all()

    assert len(non_oa_met) > 0
    for m in non_oa_met:
        report = await run_a8_activation(
            rights_mode="OPEN_ACCESS_ONLY",
            dry_run=True,
            apply=False,
            reference_key_filter=m.reference_key,
            db_session=db_session
        )
        assert report["activation_metrics"]["rights_not_eligible"] == 1
        assert report["activation_metrics"]["activated"] == 0


@pytest.mark.asyncio
async def test_hash_separation_and_coverage(db_session: AsyncSession, monkeypatch):
    """Verify source_record_sha256 and image_content_sha256 are semantically separated."""
    res = await db_session.execute(select(HistoricalReferenceMetadataModel))
    metas = res.scalars().all()
    if not metas:
        await setup_a6_and_a7(db_session)

    synthetic_jpeg = create_synthetic_jpeg_bytes(250, 250)
    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )
    await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)

    import json
    from pathlib import Path
    sidecar_path = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_images" / "historical-image-activation.json"
    with open(sidecar_path, "r", encoding="utf-8") as f:
        sidecar = json.load(f)

    records = sidecar["records"]
    assert len(records) > 0

    # Assert 100% coverage for source_record_sha256
    source_hashes = [r.get("source_record_sha256") for r in records if r.get("source_record_sha256")]
    assert len(source_hashes) == len(records)

    # Assert image_content_sha256 is present for activated (45) and None for ineligible (55)
    ineligible = [r for r in records if r.get("status") == "RIGHTS_NOT_ELIGIBLE"]
    for r in ineligible:
        assert r.get("image_content_sha256") is None
        assert r.get("source_record_sha256") is not None

    active = [r for r in records if r.get("status") in ("ACTIVATED", "ALREADY_ACTIVE")]
    for r in active:
        assert r.get("image_content_sha256") is not None
        assert r.get("source_record_sha256") is not None
        assert r.get("source_record_sha256") != r.get("image_content_sha256")


@pytest.mark.asyncio
async def test_terminal_accounting_equation_independence(db_session: AsyncSession, monkeypatch):
    """Verify each run maintains an independent terminal status equation summing to total_considered."""
    await setup_a6_and_a7(db_session)
    synthetic_jpeg = create_synthetic_jpeg_bytes(250, 250)
    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )

    # 1. Pilot run
    pilot_report = await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, limit=5, db_session=db_session)
    pilot_m = pilot_report["run_accounting"]["current_run"]
    assert pilot_m["historical_total_considered"] == 5
    assert pilot_m["activated"] == 5
    assert pilot_m["already_active"] == 0
    assert pilot_m["rights_not_eligible"] == 0
    assert pilot_m["unaccounted"] == 0
    assert pilot_m["run_equation_valid"] is True

    # 2. Initial full run
    full_report = await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)
    full_m = full_report["run_accounting"]["current_run"]
    total = full_m["historical_total_considered"]
    assert full_m["activated"] + full_m["already_active"] + full_m["rights_not_eligible"] + full_m["no_source_image"] + full_m["other_failures"] == total
    assert full_m["unaccounted"] == 0
    assert full_m["run_equation_valid"] is True

    # 3. Idempotency run
    idem_report = await run_a8_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)
    idem_m = idem_report["run_accounting"]["current_run"]
    total_idem = idem_m["historical_total_considered"]
    assert idem_m["activated"] == 0
    assert idem_m["already_active"] + idem_m["rights_not_eligible"] + idem_m["no_source_image"] + idem_m["other_failures"] == total_idem
    assert idem_m["unaccounted"] == 0
    assert idem_m["run_equation_valid"] is True


