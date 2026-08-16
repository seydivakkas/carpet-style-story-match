import json
import pytest
import uuid
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    StyleProfileStatus,
)
from app.db.models.carpet_historical_connection import HistoricalConnectionResultModel
from app.db.models.carpet_story_association import CarpetMotifAssociationModel, CarpetStoryAssociationModel
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION
from app.scripts.analyze_historical_style_dna import run_historical_batch_analysis


from tests.test_historical_image_activation import setup_a6_and_a7, create_synthetic_jpeg_bytes
from app.scripts.activate_historical_images import run_activation


@pytest.mark.asyncio
async def test_lineage_same_db_pilot_continuity(db_session: AsyncSession, monkeypatch):
    """Verify Case A: 5 pilot profiles persisted -> full run skips them as ALREADY_CURRENT."""
    await setup_a6_and_a7(db_session)
    synthetic_jpeg = create_synthetic_jpeg_bytes(200, 200)

    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )

    await run_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)

    test_rep = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-lineage-report.json"
    test_man = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-lineage-manifest.json"

    # Step 1: Pilot run (5 items) in test DB session
    pilot_report = await run_historical_batch_analysis(
        apply=True,
        pilot=True,
        limit=5,
        report_path=str(test_rep),
        run_manifest_path=str(test_man),
        db_session=db_session,
    )
    assert pilot_report["run_accounting"]["current_run"]["processed"] == 5
    assert pilot_report["run_accounting"]["current_run"]["already_current"] == 0

    # Step 2: Full run immediately following pilot in same test DB session
    full_report = await run_historical_batch_analysis(
        apply=True,
        resume=True,
        report_path=str(test_rep),
        run_manifest_path=str(test_man),
        db_session=db_session,
    )

    # In same DB session with fixture data:
    # Pilot processed 5 ready items.
    # Full run sees 5 ALREADY_CURRENT and processes the remaining ready items.
    assert full_report["already_current"] == 5
    assert full_report["processed"] == full_report["primary_image_ready"] - 5
    assert full_report["unaccounted"] == 0


@pytest.mark.asyncio
async def test_lineage_final_idempotency_state(db_session: AsyncSession, monkeypatch):
    """Verify rerun against complete state evaluates 0 processed, all ready as already_current, and 0 unaccounted."""
    await setup_a6_and_a7(db_session)
    synthetic_jpeg = create_synthetic_jpeg_bytes(200, 200)

    monkeypatch.setattr(
        "app.scripts.activate_historical_images.download_museum_image_bytes",
        lambda url, timeout=15, delay_sec=0.2: (synthetic_jpeg, "image/jpeg")
    )

    await run_activation(rights_mode="OPEN_ACCESS_ONLY", dry_run=False, apply=True, db_session=db_session)

    test_rep = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-lineage-report.json"
    test_man = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-lineage-manifest.json"

    # Step 1: Full run in test DB session
    report1 = await run_historical_batch_analysis(
        apply=True,
        resume=True,
        report_path=str(test_rep),
        run_manifest_path=str(test_man),
        db_session=db_session,
    )
    assert report1["processed"] == report1["primary_image_ready"]

    # Step 2: Rerun (0 items processed, all ready items already current)
    report2 = await run_historical_batch_analysis(
        apply=True,
        resume=True,
        report_path=str(test_rep),
        run_manifest_path=str(test_man),
        db_session=db_session,
    )

    assert report2["processed"] == 0
    assert report2["already_current"] == report2["primary_image_ready"]
    assert report2["unaccounted"] == 0


@pytest.mark.asyncio
async def test_lineage_reconciliation_json_validity():
    """Verify a9-run-lineage-reconciliation.json exists and conforms to required schema."""
    recon_path = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "a9-run-lineage-reconciliation.json"
    assert recon_path.exists(), "Reconciliation report missing"

    with open(recon_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("classification") == "CASE_A_SAME_DB_PILOT_PERSISTENCE"
    assert data.get("pilot_execution", {}).get("pilot_processed") == 5
    assert data.get("initial_full_run_execution", {}).get("full_run_processed") == 40
    assert data.get("initial_full_run_execution", {}).get("full_run_already_current") == 5
    assert data.get("final_database_state", {}).get("duplicate_current_profiles") == 0
    assert data.get("final_database_state", {}).get("current_historical_profiles") == 45
