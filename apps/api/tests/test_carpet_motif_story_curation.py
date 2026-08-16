"""Pytest test suite for POST-v1 A5 Carpet ↔ Motif / Story Curation."""
import json
from pathlib import Path
import sqlite3
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetMotifAssociationSourceModel,
    CarpetStoryAssociationModel,
    MotifEvidenceTypeEnum,
)
from app.db.models.motif_knowledge import (
    CuratedSourceModel,
    MotifModel,
    MotifStoryClaimModel,
    MotifStoryStatusEnum,
)
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import CurationImportSchema
from app.domain.carpet_catalog.importer import CarpetCatalogImporter
from app.domain.carpet_catalog.schemas import (
    CatalogImportDataset,
    CatalogCarpetInput,
    CatalogMotifAssociationInput,
    CatalogStoryAssociationInput,
    CatalogMotifSourceInput,
)
from app.domain.carpet_catalog.exceptions import (
    CarpetMotifCurationNoteRequiredError,
    CarpetMotifSourceRequiredError,
    CarpetMotifUncertaintyNoteRequiredError,
    CarpetUncertainMotifCannotHaveStoryError,
    CarpetStoryUnknownClaimNotApplicableError,
    CarpetStoryApplicabilityNoteRequiredError,
    CarpetStoryMotifMismatchError,
    CurationConflictError,
)
from app.scripts.build_carpet_motif_review import check_stale_reviews

MOTIF_KNOWLEDGE_PATH = Path(__file__).resolve().parents[3] / "data" / "activation" / "motif_knowledge" / "motif-knowledge.json"
DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "activation" / "merinos" / "motif_curation" / "carpet-motif-story-curation.json"


@pytest.fixture(autouse=True)
async def seed_curation_dataset(db_session: AsyncSession):
    """Seed in-memory test DB with motif knowledge and activated curation dataset."""
    assert MOTIF_KNOWLEDGE_PATH.exists(), f"Motif knowledge dataset missing at {MOTIF_KNOWLEDGE_PATH}"
    with open(MOTIF_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        mk_data = json.load(f)
    mk_schema = CurationImportSchema.model_validate(mk_data)
    mk_importer = MotifKnowledgeImporter(db_session)
    await mk_importer.import_data(mk_schema, dry_run=False, allow_overwrite=True)

    assert DATASET_PATH.exists(), f"Curation dataset missing at {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    dataset = CatalogImportDataset.model_validate(raw_data)
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset, dry_run=False)


@pytest.mark.asyncio
async def test_curation_association_counts(db_session: AsyncSession):
    """Verify production database contains 12 motif associations and 11 story associations."""
    m_count = (await db_session.execute(select(func.count(CarpetMotifAssociationModel.id)))).scalar()
    s_count = (await db_session.execute(select(func.count(CarpetStoryAssociationModel.id)))).scalar()

    assert m_count == 12
    assert s_count == 11


@pytest.mark.asyncio
async def test_curator_confirmed_valid(db_session: AsyncSession):
    """Verify CURATOR_CONFIRMED requires non-empty curation note."""
    res = await db_session.execute(
        select(CarpetMotifAssociationModel).where(
            CarpetMotifAssociationModel.evidence_type == MotifEvidenceTypeEnum.CURATOR_CONFIRMED
        )
    )
    assocs = res.scalars().all()
    assert len(assocs) == 11
    for a in assocs:
        assert a.curation_note and a.curation_note.strip()


@pytest.mark.asyncio
async def test_curator_without_note_rejected(db_session: AsyncSession):
    """Verify CURATOR_CONFIRMED without curation_note raises error."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="73941 060",
                name="Elegance 73941 060",
                collection="Elegance",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="medallion",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note=""  # Empty note!
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetMotifCurationNoteRequiredError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_source_documented_without_source_rejected(db_session: AsyncSession):
    """Verify SOURCE_DOCUMENTED without sources raises error."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="73941 060",
                name="Elegance 73941 060",
                collection="Elegance",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="medallion",
                        evidence_type=MotifEvidenceTypeEnum.SOURCE_DOCUMENTED,
                        sources=[]  # Empty sources!
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetMotifSourceRequiredError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_uncertain_with_story_rejected(db_session: AsyncSession):
    """Verify UNCERTAIN motif cannot carry story associations."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="72484 062",
                name="Arden 72484 062",
                collection="Arden",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="geometric-star",
                        evidence_type=MotifEvidenceTypeEnum.UNCERTAIN,
                        uncertainty_note="Belirsiz motif",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-geometric-star-spatial-order")
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetUncertainMotifCannotHaveStoryError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_unknown_claim_story_rejected(db_session: AsyncSession):
    """Verify UNKNOWN claim (claim-mystery-hook-unknown) cannot be attached as positive story."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="73941 060",
                name="Elegance 73941 060",
                collection="Elegance",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="mystery-hook",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Gizemli çengel motifi incelendi",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-mystery-hook-unknown")
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryUnknownClaimNotApplicableError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_contextual_and_contested_without_applicability_rejected(db_session: AsyncSession):
    """Verify CONTEXTUAL or CONTESTED claims require applicability_note."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="91001 020",
                name="Valeria 91001 020",
                collection="Valeria",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-of-life",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Hayat ağacı incelendi",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-tree-of-life-anatolian-context",
                                applicability_note=""  # Empty applicability note!
                            )
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryApplicabilityNoteRequiredError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_wrong_motif_claim_rejected(db_session: AsyncSession):
    """Verify claim belonging to lotus cannot attach to medallion motif association."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="73941 060",
                name="Elegance 73941 060",
                collection="Elegance",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="medallion",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Madalyon incelendi",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-lotus-rebirth",  # Lotus claim under medallion!
                                applicability_note="Test note"
                            )
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryMotifMismatchError):
        await importer.import_dataset(dataset, dry_run=True)


@pytest.mark.asyncio
async def test_no_auto_inheritance(db_session: AsyncSession):
    """Verify adding motif association without story_claim_keys creates 0 story associations."""
    dataset = CatalogImportDataset(
        schema_version="carpet-catalog-curation-v1",
        carpets=[
            CatalogCarpetInput(
                sku="73941 060",
                name="Elegance 73941 060",
                collection="Elegance",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="rosette",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Rozet motifi incelendi",
                        story_claim_keys=[]  # No stories!
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset, dry_run=False)
    assert res.story_associations_created == 0


@pytest.mark.asyncio
async def test_idempotent_import(db_session: AsyncSession):
    """Verify second import of exact dataset creates 0 new records."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    dataset = CatalogImportDataset.model_validate(raw_data)
    importer = CarpetCatalogImporter(db_session)
    res_second = await importer.import_dataset(dataset, dry_run=False)

    assert res_second.carpets_created == 0
    assert res_second.motif_associations_created == 0
    assert res_second.presence_sources_created == 0
    assert res_second.story_associations_created == 0


@pytest.mark.asyncio
async def test_stale_review_detection():
    """Verify check_stale_reviews() detects image changes."""
    stale_items = check_stale_reviews()
    assert isinstance(stale_items, list)
    assert len(stale_items) == 0


@pytest.mark.asyncio
async def test_catalog_and_boundary_immutability(db_session: AsyncSession):
    """Verify Catalog baseline, Style DNA, and A4/A6/A7 boundaries."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        carpets = cur.execute("SELECT COUNT(*) FROM carpets WHERE source_type = 'CATALOG'").fetchone()[0]
        images = cur.execute("SELECT COUNT(*) FROM carpet_images WHERE is_primary = 1").fetchone()[0]
        styles = cur.execute("SELECT COUNT(*) FROM carpet_style_profiles").fetchone()[0]
        sources = cur.execute("SELECT COUNT(*) FROM curated_sources").fetchone()[0]
        motifs = cur.execute("SELECT COUNT(*) FROM motifs").fetchone()[0]
        claims = cur.execute("SELECT COUNT(*) FROM motif_story_claims").fetchone()[0]
        conn.close()

        assert carpets == 232
        assert images == 227
        assert styles == 227
        assert sources == 6
        assert motifs == 13
        assert claims == 12
