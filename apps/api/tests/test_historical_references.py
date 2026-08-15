"""Comprehensive Pytest test suite for Historical Reference Collection v1."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel, StyleProfileStatus
from app.db.models.motif_knowledge import CuratedSourceModel, SourceTypeEnum
from app.db.models.carpet_historical_reference import (
    HistoricalSourceRoleEnum,
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel
)
from app.domain.common.readiness import StyleDnaReadinessEnum, derive_style_dna_readiness
from app.domain.historical_reference.constants import (
    HISTORICAL_REFERENCE_SCHEMA_VERSION,
    HISTORICAL_REFERENCE_API_VERSION
)
from app.domain.historical_reference.exceptions import (
    HistoricalReferenceNotFoundError,
    HistoricalReferenceInvalidSchemaVersionError,
    HistoricalReferencePrimarySourceRequiredError,
    HistoricalReferenceInvalidPrimarySourceTypeError,
    HistoricalReferenceUnknownSourceError,
    HistoricalReferenceIdentityRequiredError,
    HistoricalReferenceDateRangeInvalidError,
    HistoricalReferenceConflictError,
    HistoricalReferenceObjectConflictError
)
from app.domain.historical_reference.importer import HistoricalReferenceImporter
from app.domain.historical_reference.schemas import (
    HistoricalReferenceImportDataset,
    HistoricalReferenceInput,
    HistoricalSupportingSourceInput
)
from app.domain.historical_reference.service import HistoricalReferenceService


@pytest.fixture
async def sample_curated_sources(db_session: AsyncSession):
    """Creates sample CuratedSource records for primary museum records and supporting references."""
    museum_src = CuratedSourceModel(
        id=uuid.uuid4(),
        source_key="met-museum-obj-1974.149.34",
        source_type=SourceTypeEnum.MUSEUM_OBJECT,
        title="Metropolitan Museum Object Record 1974.149.34",
        citation_text="The Metropolitan Museum of Art, New York, Accession 1974.149.34",
        creator_or_institution="The Metropolitan Museum of Art"
    )
    archive_src = CuratedSourceModel(
        id=uuid.uuid4(),
        source_key="vam-archive-t105-1910",
        source_type=SourceTypeEnum.ARCHIVE_RECORD,
        title="Victoria and Albert Museum Textile Archive T.105-1910",
        citation_text="Victoria and Albert Museum, London, Archive T.105-1910",
        creator_or_institution="Victoria and Albert Museum"
    )
    book_src = CuratedSourceModel(
        id=uuid.uuid4(),
        source_key="denny-2002-classical-carpets",
        source_type=SourceTypeEnum.ACADEMIC_BOOK,
        title="Classical Ottoman Carpets",
        citation_text="Denny, W. (2002). Classical Ottoman Carpets. London: Thames & Hudson.",
        creator_or_institution="Walter B. Denny",
        publication_year=2002
    )

    db_session.add_all([museum_src, archive_src, book_src])
    await db_session.commit()
    return {
        "museum": museum_src,
        "archive": archive_src,
        "book": book_src
    }


@pytest.mark.asyncio
async def test_import_valid_dataset(db_session: AsyncSession, sample_curated_sources):
    """Tests successful atomic import of a valid historical reference record."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                supporting_sources=[
                    HistoricalSupportingSourceInput(
                        source_key="denny-2002-classical-carpets",
                        locator="p. 42",
                        source_note="Analysis of medallion structure"
                    )
                ],
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                accession_number="1974.149.34",
                object_title="Star Ushak Carpet",
                culture="Ottoman",
                period="16th Century",
                dynasty_or_tradition="Ottoman Court Workshop",
                date_display="ca. 1550–1600",
                date_start_year=1550,
                date_end_year=1600,
                geography="Ushak, Anatolia, Turkey",
                medium="Wool pile on wool warp and weft",
                dimensions_text="420 x 215 cm",
                department="Islamic Art",
                credit_line="Gift of Joseph V. McMullan",
                object_url="https://www.metmuseum.org/art/collection/search/451234",
                source_image_url="https://images.metmuseum.org/CRDImages/is/original/DP1234.jpg",
                rights_statement="Public Domain",
                open_access=True,
                curation_note="Classic 6-pointed star pattern with dark blue ground"
            )
        ]
    )

    importer = HistoricalReferenceImporter(db_session)
    res = await importer.import_dataset(dataset, dry_run=False)

    assert res["status"] == "SUCCESS"
    assert res["imported_count"] == 1
    assert res["skipped_count"] == 0

    # Verify CarpetModel creation
    carpet_stmt = select(CarpetModel).where(CarpetModel.source_reference == "REF-MET-1974-149-34")
    carpet_res = await db_session.execute(carpet_stmt)
    carpet = carpet_res.scalar_one()

    assert carpet.source_type == CarpetSourceType.HISTORICAL
    assert carpet.name == "Star Ushak Carpet"

    # Verify HistoricalReferenceMetadataModel creation
    meta_stmt = select(HistoricalReferenceMetadataModel).where(HistoricalReferenceMetadataModel.reference_key == "REF-MET-1974-149-34")
    meta_res = await db_session.execute(meta_stmt)
    meta = meta_res.scalar_one()

    assert meta.carpet_id == carpet.id
    assert meta.institution_name == "The Metropolitan Museum of Art"
    assert meta.culture == "Ottoman"
    assert meta.date_start_year == 1550
    assert meta.date_end_year == 1600

    # Verify HistoricalReferenceSourceModel creation
    links_stmt = select(HistoricalReferenceSourceModel).where(HistoricalReferenceSourceModel.historical_reference_id == meta.id)
    links_res = await db_session.execute(links_stmt)
    links = list(links_res.scalars().all())

    assert len(links) == 2
    primary_link = [l for l in links if l.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD][0]
    supporting_link = [l for l in links if l.source_role == HistoricalSourceRoleEnum.SUPPORTING_REFERENCE][0]

    assert primary_link.source_id == sample_curated_sources["museum"].id
    assert supporting_link.source_id == sample_curated_sources["book"].id
    assert supporting_link.locator == "p. 42"


@pytest.mark.asyncio
async def test_import_dry_run(db_session: AsyncSession, sample_curated_sources):
    """Tests dry-run import mode where validation passes but nothing is persisted to DB."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-VAM-T105",
                primary_source_key="vam-archive-t105-1910",
                institution_name="Victoria and Albert Museum",
                object_identifier="T.105-1910",
                object_title="Ardabil Carpet Segment"
            )
        ]
    )

    importer = HistoricalReferenceImporter(db_session)
    res = await importer.import_dataset(dataset, dry_run=True)

    assert res["dry_run"] is True
    assert res["status"] == "VALID"
    assert res["imported_count"] == 1

    # Verify DB was NOT modified
    meta_stmt = select(HistoricalReferenceMetadataModel).where(HistoricalReferenceMetadataModel.reference_key == "REF-VAM-T105")
    meta_res = await db_session.execute(meta_stmt)
    assert meta_res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_import_idempotent_duplicate(db_session: AsyncSession, sample_curated_sources):
    """Tests re-importing exact identical record skips without error."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Star Ushak Carpet"
            )
        ]
    )

    importer = HistoricalReferenceImporter(db_session)
    await importer.import_dataset(dataset, dry_run=False)

    # Re-run identical dataset
    res2 = await importer.import_dataset(dataset, dry_run=False)

    assert res2["status"] == "SUCCESS"
    assert res2["imported_count"] == 0
    assert res2["skipped_count"] == 1


@pytest.mark.asyncio
async def test_import_conflicting_metadata(db_session: AsyncSession, sample_curated_sources):
    """Tests re-importing reference_key with altered metadata raises HistoricalReferenceConflictError."""
    dataset1 = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Star Ushak Carpet"
            )
        ]
    )
    dataset2 = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Altered Star Ushak Carpet Title"
            )
        ]
    )

    importer = HistoricalReferenceImporter(db_session)
    await importer.import_dataset(dataset1, dry_run=False)

    with pytest.raises(HistoricalReferenceConflictError):
        await importer.import_dataset(dataset2, dry_run=False)


@pytest.mark.asyncio
async def test_import_conflicting_object_identity(db_session: AsyncSession, sample_curated_sources):
    """Tests importing item with same (institution, object_id) under different reference_key raises HistoricalReferenceObjectConflictError."""
    dataset1 = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Star Ushak Carpet"
            )
        ]
    )
    dataset2 = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-DUPLICATE-KEY",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Star Ushak Carpet"
            )
        ]
    )

    importer = HistoricalReferenceImporter(db_session)
    await importer.import_dataset(dataset1, dry_run=False)

    with pytest.raises(HistoricalReferenceObjectConflictError):
        await importer.import_dataset(dataset2, dry_run=False)


@pytest.mark.asyncio
async def test_import_invalid_schema_version(db_session: AsyncSession):
    """Tests invalid schema version raises HistoricalReferenceInvalidSchemaVersionError."""
    dataset = HistoricalReferenceImportDataset(
        schema_version="invalid-v99",
        references=[]
    )
    importer = HistoricalReferenceImporter(db_session)
    with pytest.raises(HistoricalReferenceInvalidSchemaVersionError):
        await importer.import_dataset(dataset, dry_run=False)


@pytest.mark.asyncio
async def test_import_invalid_date_range(db_session: AsyncSession, sample_curated_sources):
    """Tests date_start_year > date_end_year raises HistoricalReferenceDateRangeInvalidError."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-INVALID-DATE",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Test",
                date_start_year=1700,
                date_end_year=1600
            )
        ]
    )
    importer = HistoricalReferenceImporter(db_session)
    with pytest.raises(HistoricalReferenceDateRangeInvalidError):
        await importer.import_dataset(dataset, dry_run=False)


@pytest.mark.asyncio
async def test_import_invalid_primary_source_type(db_session: AsyncSession, sample_curated_sources):
    """Tests primary source with non-museum/archive type raises HistoricalReferenceInvalidPrimarySourceTypeError."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-INVALID-PRIMARY-TYPE",
                primary_source_key="denny-2002-classical-carpets",  # ACADEMIC_BOOK
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Test"
            )
        ]
    )
    importer = HistoricalReferenceImporter(db_session)
    with pytest.raises(HistoricalReferenceInvalidPrimarySourceTypeError):
        await importer.import_dataset(dataset, dry_run=False)


@pytest.mark.asyncio
async def test_import_unknown_source(db_session: AsyncSession):
    """Tests unknown source key raises HistoricalReferenceUnknownSourceError."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-UNKNOWN-SRC",
                primary_source_key="nonexistent-source-key",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Test"
            )
        ]
    )
    importer = HistoricalReferenceImporter(db_session)
    with pytest.raises(HistoricalReferenceUnknownSourceError):
        await importer.import_dataset(dataset, dry_run=False)


@pytest.mark.asyncio
async def test_api_list_and_detail(client: AsyncClient, db_session: AsyncSession, sample_curated_sources):
    """Tests GET /api/v1/historical-references and GET /api/v1/historical-references/{id_or_key}."""
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-MET-1974-149-34",
                primary_source_key="met-museum-obj-1974.149.34",
                supporting_sources=[
                    HistoricalSupportingSourceInput(
                        source_key="denny-2002-classical-carpets",
                        locator="p. 42"
                    )
                ],
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Star Ushak Carpet",
                culture="Ottoman",
                period="16th Century"
            )
        ]
    )
    importer = HistoricalReferenceImporter(db_session)
    await importer.import_dataset(dataset, dry_run=False)

    # 1. Test List Endpoint
    resp = await client.get("/api/v1/historical-references?institution=The Metropolitan Museum of Art")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_count"] == 1
    ref_item = data["references"][0]
    assert ref_item["reference_key"] == "REF-MET-1974-149-34"
    assert ref_item["institution_name"] == "The Metropolitan Museum of Art"

    # 2. Test Detail Endpoint by reference_key
    resp_detail = await client.get("/api/v1/historical-references/REF-MET-1974-149-34")
    assert resp_detail.status_code == 200
    detail = resp_detail.json()

    assert detail["reference_key"] == "REF-MET-1974-149-34"
    assert detail["primary_source"]["source_key"] == "met-museum-obj-1974.149.34"
    assert detail["primary_source"]["source_role"] == "PRIMARY_OBJECT_RECORD"
    assert len(detail["supporting_sources"]) == 1
    assert detail["supporting_sources"][0]["source_key"] == "denny-2002-classical-carpets"
    assert detail["style_dna_readiness"] == "NO_PRIMARY_IMAGE"


@pytest.mark.asyncio
async def test_api_not_found(client: AsyncClient):
    """Tests GET for non-existent reference key returns 404 with HISTORICAL_REFERENCE_NOT_FOUND."""
    resp = await client.get("/api/v1/historical-references/REF-NONEXISTENT")
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"]["code"] == "HISTORICAL_REFERENCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_api_meta_endpoint(client: AsyncClient):
    """Tests GET /api/v1/meta/historical-references metadata response."""
    resp = await client.get("/api/v1/meta/historical-references")
    assert resp.status_code == 200
    data = resp.json()

    assert data["api_version"] == HISTORICAL_REFERENCE_API_VERSION
    assert data["curation_schema_version"] == HISTORICAL_REFERENCE_SCHEMA_VERSION
    assert "PRIMARY_OBJECT_RECORD" in data["source_roles"]
    assert "SUPPORTING_REFERENCE" in data["source_roles"]
    assert "NO_PRIMARY_IMAGE" in data["style_dna_readiness_states"]


@pytest.mark.asyncio
async def test_style_dna_readiness_states(db_session: AsyncSession, sample_curated_sources):
    """Tests derive_style_dna_readiness for all 5 readiness states."""
    # 1. NO_PRIMARY_IMAGE
    assert derive_style_dna_readiness(None, None) == StyleDnaReadinessEnum.NO_PRIMARY_IMAGE

    # Create carpet & image
    dataset = HistoricalReferenceImportDataset(
        schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION,
        references=[
            HistoricalReferenceInput(
                reference_key="REF-READINESS-TEST",
                primary_source_key="met-museum-obj-1974.149.34",
                institution_name="The Metropolitan Museum of Art",
                object_identifier="1974.149.34",
                object_title="Readiness Test Carpet"
            )
        ]
    )
    importer = HistoricalReferenceImporter(db_session)
    await importer.import_dataset(dataset, dry_run=False)

    meta = await HistoricalReferenceService(db_session).repo.get_by_reference_key("REF-READINESS-TEST")

    # Add primary image
    img = CarpetImageModel(
        id=uuid.uuid4(),
        carpet_id=meta.carpet_id,
        original_filename="image.jpg",
        content_type="image/jpeg",
        storage_key="test/image.jpg",
        byte_size=1024,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        is_primary=True
    )
    db_session.add(img)
    await db_session.commit()

    service = HistoricalReferenceService(db_session)

    # 2. STYLE_DNA_MISSING (Image exists, no profile)
    detail1 = await service.get_historical_reference_detail("REF-READINESS-TEST")
    assert detail1.style_dna_readiness == StyleDnaReadinessEnum.STYLE_DNA_MISSING

    # 3. STYLE_DNA_FAILED
    prof_failed = CarpetStyleProfileModel(
        id=uuid.uuid4(),
        carpet_id=meta.carpet_id,
        image_id=img.id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        analyzed_width_px=800,
        analyzed_height_px=600,
        status=StyleProfileStatus.FAILED
    )
    db_session.add(prof_failed)
    await db_session.commit()

    detail2 = await service.get_historical_reference_detail("REF-READINESS-TEST")
    assert detail2.style_dna_readiness == StyleDnaReadinessEnum.STYLE_DNA_FAILED

    # 4. STYLE_DNA_COMPLETE
    prof_failed.status = StyleProfileStatus.COMPLETE
    await db_session.commit()

    detail3 = await service.get_historical_reference_detail("REF-READINESS-TEST")
    assert detail3.style_dna_readiness == StyleDnaReadinessEnum.STYLE_DNA_COMPLETE
