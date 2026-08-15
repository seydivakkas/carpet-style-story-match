"""Unit tests for Merinos catalog false-positive cleanup utility script."""
import os
import json
import uuid
import pytest
from sqlalchemy import select, func
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.scripts.cleanup_merinos_catalog_false_positives import run_cleanup_async


@pytest.mark.asyncio
async def test_cleanup_script_dry_run_and_apply(db_session, tmp_path):
    # Setup test carpets in DB (1 valid product, 1 false-positive blog archive)
    c1 = CarpetModel(
        id=uuid.uuid4(),
        sku="TEST-VALID-001",
        name="Valid Carpet 001",
        source_type=CarpetSourceType.CATALOG,
        source_reference="https://www.merinos.com.tr/90823-070",
        is_active=True
    )
    c2 = CarpetModel(
        id=uuid.uuid4(),
        sku="2024 10",
        name="Blog Archive 2024 10",
        source_type=CarpetSourceType.CATALOG,
        source_reference="https://www.merinos.com.tr/blog/month/2024-10",
        is_active=True
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    source_file = tmp_path / "test_source.json"
    source_file.write_text(json.dumps({
        "products": [
            {"sku": "TEST-VALID-001", "source_url": "https://www.merinos.com.tr/90823-070"}
        ]
    }))
    out_report = str(tmp_path / "cleanup_report.json")

    # 1. Test Dry-Run Mode
    await run_cleanup_async(
        dry_run=True,
        apply=False,
        source_file=str(source_file),
        output_report=out_report,
        session=db_session
    )

    # Verify report created and 0 rows deleted
    rep1 = json.loads(open(out_report, encoding="utf-8").read())
    assert rep1["dry_run"] is True
    assert rep1["false_positive_candidates"] == 1
    assert rep1["deleted"] == 0

    res1 = (await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.sku == "2024 10"))).scalar_one()
    assert res1 == 1  # Still in DB

    # 2. Test Apply Mode
    await run_cleanup_async(
        dry_run=False,
        apply=True,
        source_file=str(source_file),
        output_report=out_report,
        session=db_session
    )

    rep2 = json.loads(open(out_report, encoding="utf-8").read())
    assert rep2["applied"] is True
    assert rep2["deleted"] == 1

    res2 = (await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.sku == "2024 10"))).scalar_one()
    assert res2 == 0  # Deleted from DB

    res_valid = (await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.sku == "TEST-VALID-001"))).scalar_one()
    assert res_valid == 1  # Valid product strictly preserved!
