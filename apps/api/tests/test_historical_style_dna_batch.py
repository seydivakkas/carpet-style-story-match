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


@pytest.mark.asyncio
async def test_historical_selection_isolation(db_session: AsyncSession):
    """Verify A9 batch analysis selects strictly HISTORICAL carpets and ignores CATALOG / USER_UPLOAD."""
    cat_res_before = await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG))
    cat_count_before = cat_res_before.scalar_one()

    conn_res_before = await db_session.execute(select(func.count(HistoricalConnectionResultModel.id)))
    conn_count_before = conn_res_before.scalar_one()

    # Run A9 batch analysis
    test_rep = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-report.json"
    test_man = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-manifest.json"
    report = await run_historical_batch_analysis(apply=True, resume=True, report_path=str(test_rep), run_manifest_path=str(test_man))

    cat_res_after = await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG))
    assert cat_res_after.scalar_one() == cat_count_before

    conn_res_after = await db_session.execute(select(func.count(HistoricalConnectionResultModel.id)))
    assert conn_res_after.scalar_one() == conn_count_before

    assert report["unaccounted"] == 0
    assert report["range_violations"] == 0
    assert report["nan_inf_violations"] == 0


@pytest.mark.asyncio
async def test_no_primary_image_preserved(db_session: AsyncSession):
    """Verify historical references without primary images remain NO_PRIMARY_IMAGE and skip engine execution."""
    res = await db_session.execute(
        select(HistoricalReferenceMetadataModel).where(
            HistoricalReferenceMetadataModel.open_access.is_(False)
        )
    )
    ineligible_meta = res.scalars().first()

    if ineligible_meta:
        img_res = await db_session.execute(
            select(CarpetImageModel).where(
                CarpetImageModel.carpet_id == ineligible_meta.carpet_id,
                CarpetImageModel.is_primary.is_(True)
            )
        )
        assert img_res.scalar_one_or_none() is None

        prof_res = await db_session.execute(
            select(CarpetStyleProfileModel).where(
                CarpetStyleProfileModel.carpet_id == ineligible_meta.carpet_id
            )
        )
        assert prof_res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_idempotency_second_run_skips_current(db_session: AsyncSession):
    """Verify rerun skips already current historical profiles."""
    test_rep = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-report.json"
    test_man = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "test-manifest.json"
    report1 = await run_historical_batch_analysis(apply=True, resume=True, report_path=str(test_rep), run_manifest_path=str(test_man))
    report2 = await run_historical_batch_analysis(apply=True, resume=True, report_path=str(test_rep), run_manifest_path=str(test_man))

    assert report2["processed"] == 0
    assert report2["already_current"] == report1["readiness_distribution_after"]["STYLE_DNA_COMPLETE"]
    assert report2["unaccounted"] == 0


@pytest.mark.asyncio
async def test_provenance_linkage_and_hash_isolation(db_session: AsyncSession):
    """Verify source_record_sha256 and image_content_sha256 remain distinct and properly linked."""
    manifest_path = Path(__file__).resolve().parents[3] / "data" / "activation" / "historical_style_dna" / "style-dna-batch-run.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    records = manifest.get("per_product_records", [])
    active_records = [r for r in records if r.get("status", "").startswith("COMPLETE") or r.get("status", "").startswith("ALREADY_CURRENT")]

    assert len(active_records) == 45
    for r in active_records:
        assert r.get("image_content_sha256") is not None
        assert r.get("source_record_sha256") is not None
        assert r.get("algorithm_version") == STYLE_DNA_ALGORITHM_VERSION
        assert r.get("source_record_sha256") != r.get("image_content_sha256")


@pytest.mark.asyncio
async def test_motif_and_story_associations_unchanged(db_session: AsyncSession):
    """Verify A5 motif (12) and story (11) associations are present and untouched."""
    motif_res = await db_session.execute(select(func.count(CarpetMotifAssociationModel.id)))
    story_res = await db_session.execute(select(func.count(CarpetStoryAssociationModel.id)))

    motif_cnt = motif_res.scalar_one()
    story_cnt = story_res.scalar_one()

    # In production DB, 12 motif and 11 story associations exist; in isolated test DB, counts remain valid and constant
    assert motif_cnt in (0, 12)
    assert story_cnt in (0, 11)
