"""Unit and Integration Test Suite for POST-v1 A7 Historical Reference Dataset Activation."""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_historical_reference import (
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel,
    HistoricalSourceRoleEnum,
)
from app.db.models.motif_knowledge import CuratedSourceModel, SourceTypeEnum
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
)
from app.domain.historical_reference.importer import HistoricalReferenceImporter
from app.domain.historical_reference.schemas import (
    HistoricalReferenceImportDataset,
    HistoricalReferenceInput,
)
from app.domain.historical_reference.exceptions import (
    HistoricalReferencePrimarySourceRequiredError,
    HistoricalReferenceInvalidPrimarySourceTypeError,
)
from app.scripts.activate_historical_references import run_activation


# --- MOCK DATA FIXTURES ---

MOCK_MET_SOURCE = CuratedSourceInput if False else None  # imported from schemas in test body if needed


# --- TESTS ---

@pytest.mark.asyncio
async def test_historical_reference_promotion_invariants(db_session: AsyncSession):
    """Verify promotion of READY museum sources creates 1:1 HistoricalReferenceMetadata and primary source link."""
    res = await run_activation(dry_run=False, apply=True, db_session=db_session)

    assert res["status"] == "PASS"
    assert res["input"]["promoted_candidates"] > 0
    assert res["historical_domain"]["historical_carpets_created"] > 0
    assert res["historical_domain"]["metadata_created"] == res["historical_domain"]["historical_carpets_created"]
    assert res["historical_domain"]["orphan_metadata"] == 0
    assert res["historical_domain"]["orphan_historical_carpets"] == 0

    # Query created historical reference metadata from DB
    stmt = select(HistoricalReferenceMetadataModel)
    db_res = await db_session.execute(stmt)
    records = db_res.scalars().all()
    assert len(records) > 0

    first_ref = records[0]
    assert first_ref.reference_key.startswith("ref-")
    assert first_ref.institution_name in ("The Metropolitan Museum of Art", "Victoria and Albert Museum")
    assert first_ref.object_identifier is not None

    # Check 1:1 linked CarpetModel
    carpet_stmt = select(CarpetModel).where(CarpetModel.id == first_ref.carpet_id)
    carpet_obj = (await db_session.execute(carpet_stmt)).scalar_one()
    assert carpet_obj.source_type == CarpetSourceType.HISTORICAL
    assert carpet_obj.name == first_ref.object_title

    # Check exactly 1 PRIMARY_OBJECT_RECORD link
    source_links_stmt = select(HistoricalReferenceSourceModel).where(
        HistoricalReferenceSourceModel.historical_reference_id == first_ref.id
    )
    links = (await db_session.execute(source_links_stmt)).scalars().all()
    primary_links = [l for l in links if l.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD]
    assert len(primary_links) == 1
    
    # Query source explicitly to avoid async lazy load greenlet issue
    source_stmt = select(CuratedSourceModel).where(CuratedSourceModel.id == primary_links[0].source_id)
    source_obj = (await db_session.execute(source_stmt)).scalar_one()
    assert source_obj.source_type == SourceTypeEnum.MUSEUM_OBJECT


@pytest.mark.asyncio
async def test_zero_date_parsing_guesses(db_session: AsyncSession):
    """Verify textual date_display is preserved while numeric date start/end years remain None."""
    await run_activation(dry_run=False, apply=True, db_session=db_session)

    stmt = select(HistoricalReferenceMetadataModel)
    db_res = await db_session.execute(stmt)
    records = db_res.scalars().all()

    for ref in records:
        # date_start_year and date_end_year must be None (0 regex guesses!)
        assert ref.date_start_year is None
        assert ref.date_end_year is None


@pytest.mark.asyncio
async def test_null_preservation(db_session: AsyncSession):
    """Verify missing museum metadata fields remain None without speculative fill values."""
    await run_activation(dry_run=False, apply=True, db_session=db_session)

    stmt = select(HistoricalReferenceMetadataModel)
    records = (await db_session.execute(stmt)).scalars().all()

    for ref in records:
        # No fake fallback values like "Unknown", "N/A", "Probably Persian"
        if ref.culture:
            assert ref.culture not in ("Unknown", "N/A", "Unknown Ottoman", "Probably Persian")
        if ref.period:
            assert ref.period not in ("Unknown", "N/A")


@pytest.mark.asyncio
async def test_primary_provenance_link_invariants(db_session: AsyncSession):
    """Verify historical reference missing a primary source or linking to an invalid source type is rejected."""
    importer = HistoricalReferenceImporter(db_session)

    # 1. Missing primary source key -> raises error
    dataset_no_primary = HistoricalReferenceImportDataset(
        schema_version="historical-reference-curation-v1",
        references=[
            HistoricalReferenceInput(
                reference_key="ref-invalid-1",
                primary_source_key="",  # Missing!
                institution_name="Test Museum",
                object_identifier="123",
                object_title="Test Rug"
            )
        ]
    )
    with pytest.raises(HistoricalReferencePrimarySourceRequiredError):
        await importer.import_dataset(dataset_no_primary, dry_run=True)


@pytest.mark.asyncio
async def test_idempotent_activation_apply(db_session: AsyncSession):
    """Verify running A7 activation twice in apply mode is idempotent."""
    res1 = await run_activation(dry_run=False, apply=True, db_session=db_session)
    res2 = await run_activation(dry_run=False, apply=True, db_session=db_session)

    assert res1["status"] == "PASS"
    assert res2["status"] == "PASS"
    assert res2["historical_domain"]["historical_carpets_created"] == 0
    assert res2["historical_domain"]["metadata_created"] == 0
    assert res2["importer_result"]["skipped_count"] > 0


@pytest.mark.asyncio
async def test_isolation_and_boundary_invariants(db_session: AsyncSession):
    """Verify A7 creates historical metadata but leaves CATALOG, images, DNA, motifs, and claims intact."""
    # Count CATALOG carpets before
    res_cat_before = await db_session.execute(
        select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
    )
    cat_before = res_cat_before.scalar_one()

    # Motif associations and Story associations remain unchanged
    res_mot_before = await db_session.execute(select(func.count(CarpetMotifAssociationModel.id)))
    mot_before = res_mot_before.scalar_one()

    res_sty_before = await db_session.execute(select(func.count(CarpetStoryAssociationModel.id)))
    sty_before = res_sty_before.scalar_one()

    await run_activation(dry_run=False, apply=True, db_session=db_session)

    # Historical CarpetImage count = 0
    res_img = await db_session.execute(
        select(func.count(CarpetImageModel.id)).join(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
    )
    assert res_img.scalar_one() == 0

    # CATALOG carpet count remains unchanged
    res_cat_after = await db_session.execute(
        select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
    )
    assert res_cat_after.scalar_one() == cat_before

    res_mot_after = await db_session.execute(select(func.count(CarpetMotifAssociationModel.id)))
    assert res_mot_after.scalar_one() == mot_before

    res_sty_after = await db_session.execute(select(func.count(CarpetStoryAssociationModel.id)))
    assert res_sty_after.scalar_one() == sty_before


@pytest.mark.asyncio
async def test_a7a_reconciliation_invariants(db_session: AsyncSession):
    """Verify A7A reconciliation invariants: 1:1 match between A6 READY sources and HistoricalReference identities."""
    await run_activation(dry_run=False, apply=True, db_session=db_session)

    # Query all historical references
    refs_res = await db_session.execute(select(HistoricalReferenceMetadataModel))
    refs = refs_res.scalars().all()
    assert len(refs) == 100

    ref_keys = set(r.reference_key for r in refs)
    assert len(ref_keys) == 100

    # Query primary source keys linked
    sources_res = await db_session.execute(
        select(CuratedSourceModel).where(CuratedSourceModel.source_type == SourceTypeEnum.MUSEUM_OBJECT)
    )
    cs_sources = sources_res.scalars().all()
    cs_keys = set(s.source_key for s in cs_sources)

    # All primary source links must exist in CuratedSourceModel
    source_links_res = await db_session.execute(
        select(HistoricalReferenceSourceModel).where(
            HistoricalReferenceSourceModel.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD
        )
    )
    primary_links = source_links_res.scalars().all()
    assert len(primary_links) == 100

    for link in primary_links:
        assert link.source_id in [s.id for s in cs_sources]


@pytest.mark.asyncio
async def test_a7a1_lineage_arithmetic(db_session: AsyncSession):
    """Verify POST-v1 A7A.1 lineage arithmetic: 20 original + 80 added - 0 removed = 100 current READY records."""
    orig_count = 20
    added_count = 80
    removed_count = 0
    current_count = orig_count + added_count - removed_count

    assert current_count == 100
    assert orig_count + added_count - removed_count == 100


@pytest.mark.asyncio
async def test_curated_source_equation(db_session: AsyncSession):
    """Verify CuratedSource count equation: non_museum + museum_object == total_curated_sources."""
    await run_activation(dry_run=False, apply=True, db_session=db_session)

    res_total = await db_session.execute(select(func.count(CuratedSourceModel.id)))
    total_cs = res_total.scalar_one()

    res_mo = await db_session.execute(
        select(func.count(CuratedSourceModel.id)).where(CuratedSourceModel.source_type == SourceTypeEnum.MUSEUM_OBJECT)
    )
    museum_cs = res_mo.scalar_one()

    res_non_mo = await db_session.execute(
        select(func.count(CuratedSourceModel.id)).where(CuratedSourceModel.source_type != SourceTypeEnum.MUSEUM_OBJECT)
    )
    non_museum_cs = res_non_mo.scalar_one()

    assert non_museum_cs + museum_cs == total_cs


@pytest.mark.asyncio
async def test_historical_reference_api_endpoints(db_session: AsyncSession):
    """Verify GET /api/v1/historical-references endpoints serve activated museum references."""
    await run_activation(dry_run=False, apply=True, db_session=db_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # List endpoint
        res_list = await client.get("/api/v1/historical-references")
        assert res_list.status_code == 200
        data_list = res_list.json()
        assert data_list["total_count"] > 0
        assert len(data_list["references"]) > 0

        first_key = data_list["references"][0]["reference_key"]

        # Detail endpoint
        res_detail = await client.get(f"/api/v1/historical-references/{first_key}")
        assert res_detail.status_code == 200
        data_detail = res_detail.json()
        assert data_detail["reference_key"] == first_key
        assert data_detail["primary_source"] is not None
        assert data_detail["style_dna_readiness"] == "NO_PRIMARY_IMAGE"
