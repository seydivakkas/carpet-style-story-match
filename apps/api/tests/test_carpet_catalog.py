"""Comprehensive Pytest test suite for Carpet Catalog + Curated Story Associations v1."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel, StyleProfileStatus
from app.db.models.carpet_story_association import MotifEvidenceTypeEnum
from app.db.models.motif_knowledge import MotifStoryStatusEnum
from app.domain.carpet_catalog.constants import CARPET_CATALOG_SCHEMA_VERSION
from app.domain.carpet_catalog.exceptions import (
    CatalogCarpetNotFoundError,
    CatalogSkuRequiredError,
    CatalogConflictError,
    CatalogSkuConflictError,
    CatalogUnknownMotifError,
    CatalogUnknownSourceError,
    CatalogUnknownClaimError,
    CarpetMotifSourceRequiredError,
    CarpetMotifCurationNoteRequiredError,
    CarpetMotifUncertaintyNoteRequiredError,
    CarpetUncertainMotifCannotHaveStoryError,
    CarpetStoryMotifMismatchError,
    CarpetStoryUnknownClaimNotApplicableError,
    CarpetStoryApplicabilityNoteRequiredError,
    CurationConflictError,
)
from app.domain.carpet_catalog.importer import CarpetCatalogImporter
from app.domain.carpet_catalog.schemas import (
    CatalogImportDataset,
    CatalogCarpetInput,
    CatalogMotifAssociationInput,
    CatalogMotifSourceInput,
    CatalogStoryAssociationInput,
    StyleDnaReadinessEnum,
)
from app.domain.carpet_catalog.service import CarpetCatalogService
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import (
    CurationImportSchema,
    SourceImportItem,
    MotifImportItem,
    ClaimImportItem,
    ClaimSourceLinkImportItem,
)
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION


async def _seed_motif_knowledge(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[
            SourceImportItem(source_key="src-1", title="Source 1", citation_text="Cit 1"),
            SourceImportItem(source_key="src-2", title="Source 2", citation_text="Cit 2")
        ],
        motifs=[
            MotifImportItem(motif_key="star-motif", name_tr="Yıldız Motif"),
            MotifImportItem(motif_key="tree-motif", name_tr="Hayat Ağacı")
        ],
        claims=[
            ClaimImportItem(
                claim_key="claim-star-doc",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yıldız kozmik düzeni temsil eder.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["balance_order"]
            ),
            ClaimImportItem(
                claim_key="claim-tree-contextual",
                motif_key="tree-motif",
                status=MotifStoryStatusEnum.CONTEXTUAL,
                claim_text_tr="İç Anadolu kültüründe soy devamlılığını simgeler.",
                context_note="19. yy İç Anadolu",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["continuity_connection"]
            ),
            ClaimImportItem(
                claim_key="claim-tree-contested",
                motif_key="tree-motif",
                status=MotifStoryStatusEnum.CONTESTED,
                claim_text_tr="Farklı kaynaklar tarafından doğa döngüsü veya cennet sembolü olarak yorumlanır.",
                contest_note="A yazarı doğa, B yazarı cennet kabul eder.",
                source_links=[
                    ClaimSourceLinkImportItem(source_key="src-1"),
                    ClaimSourceLinkImportItem(source_key="src-2")
                ],
                theme_keys=["nature_growth"]
            ),
            ClaimImportItem(
                claim_key="claim-star-unk",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr=None,
                uncertainty_note="Belirsiz",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema)


@pytest.mark.asyncio
async def test_basic_catalog_import(db_session: AsyncSession):
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-001",
                name="Anadolu Halısı",
                manufacturer="Hereke Zanaat",
                collection="Kültürel Serisi",
                width_cm=150.0,
                height_cm=200.0,
                material="Yün"
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.carpets_created == 1

    service = CarpetCatalogService(db_session)
    detail = await service.get_catalog_carpet_detail("CAT-001")
    assert detail.carpet.source_type == CarpetSourceType.CATALOG
    assert detail.carpet.manufacturer == "Hereke Zanaat"


@pytest.mark.asyncio
async def test_sku_required(db_session: AsyncSession):
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="   ",
                name="Invalid Carpet"
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CatalogSkuRequiredError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_idempotent_catalog_import(db_session: AsyncSession):
    dataset = CatalogImportDataset(
        carpets=[CatalogCarpetInput(sku="CAT-IDEM", name="Idem Carpet")]
    )

    importer = CarpetCatalogImporter(db_session)
    res1 = await importer.import_dataset(dataset)
    assert res1.carpets_created == 1

    res2 = await importer.import_dataset(dataset)
    assert res2.carpets_created == 0


@pytest.mark.asyncio
async def test_catalog_conflict(db_session: AsyncSession):
    dataset1 = CatalogImportDataset(
        carpets=[CatalogCarpetInput(sku="CAT-CONF", name="Original Name")]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset1)

    dataset2 = CatalogImportDataset(
        carpets=[CatalogCarpetInput(sku="CAT-CONF", name="Different Name")]
    )

    with pytest.raises(CatalogConflictError) as exc:
        await importer.import_dataset(dataset2)
    assert "metadata conflicts" in str(exc.value)


@pytest.mark.asyncio
async def test_sku_non_catalog_conflict(db_session: AsyncSession):
    # Add non-catalog carpet with SKU
    carpet = CarpetModel(
        id=uuid.uuid4(),
        sku="SKU-USER-1",
        name="User Carpet",
        source_type=CarpetSourceType.USER_UPLOAD
    )
    db_session.add(carpet)
    await db_session.commit()

    dataset = CatalogImportDataset(
        carpets=[CatalogCarpetInput(sku="SKU-USER-1", name="Catalog Try")]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CatalogSkuConflictError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_unknown_motif_key(db_session: AsyncSession):
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-BAD-MOTIF",
                name="Bad Motif Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="nonexistent-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note"
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CatalogUnknownMotifError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_source_documented_presence(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-SRC-DOC",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.SOURCE_DOCUMENTED,
                        sources=[CatalogMotifSourceInput(source_key="src-1", locator="p. 42")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.presence_sources_created == 1


@pytest.mark.asyncio
async def test_source_documented_without_source_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-SRC-FAIL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.SOURCE_DOCUMENTED,
                        sources=[]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetMotifSourceRequiredError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_curator_confirmed_presence(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CUR-CONF",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Curator inspection 2026-08-15."
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.motif_associations_created == 1


@pytest.mark.asyncio
async def test_curator_confirmed_without_note_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CUR-FAIL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note=None
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetMotifCurationNoteRequiredError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_uncertain_presence(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-UNCERTAIN",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.UNCERTAIN,
                        uncertainty_note="Deforme olmuş, kesinleştirilemedi.",
                        story_claim_keys=[]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.motif_associations_created == 1


@pytest.mark.asyncio
async def test_uncertain_with_story_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-UNC-STORY-FAIL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.UNCERTAIN,
                        uncertainty_note="Deforme motif",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetUncertainMotifCannotHaveStoryError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_motif_claim_mismatch_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-MISMATCH",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed star motif",
                        # claim-tree-contextual belongs to tree-motif, not star-motif!
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-tree-contextual", applicability_note="Note")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryMotifMismatchError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_documented_claim_link(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-DOC-CLAIM",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed star",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.story_associations_created == 1


@pytest.mark.asyncio
async def test_contextual_claim_note(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CTX-CLAIM",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed tree",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-tree-contextual",
                                applicability_note="Bu halı 19.yy İç Anadolu dokuma bölgesine aittir."
                            )
                        ]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset)
    assert res.story_associations_created == 1


@pytest.mark.asyncio
async def test_contextual_without_applicability_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CTX-FAIL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed tree",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-tree-contextual",
                                applicability_note=None
                            )
                        ]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryApplicabilityNoteRequiredError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_contested_claim_note(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CNT-CLAIM",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed tree",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-tree-contested",
                                applicability_note="Halı motif kompozisyonunda her iki yorum alanı da tartışmalıdır."
                            )
                        ]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    service = CarpetCatalogService(db_session)
    stories = await service.list_carpet_story_associations("CAT-CNT-CLAIM")
    assert len(stories) == 1
    assert stories[0].status == MotifStoryStatusEnum.CONTESTED


@pytest.mark.asyncio
async def test_unknown_claim_rejected(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-UNK-FAIL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed star",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-unk")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetStoryUnknownClaimNotApplicableError):
        await importer.import_dataset(dataset)


@pytest.mark.asyncio
async def test_motif_does_not_inherit_claims(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # tree-motif has 2 claims in seed, but we attach 0 explicit claims
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-NO-CLAIM-INHERIT",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed tree motif",
                        story_claim_keys=[]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    service = CarpetCatalogService(db_session)
    motifs = await service.list_carpet_motifs("CAT-NO-CLAIM-INHERIT")
    stories = await service.list_carpet_story_associations("CAT-NO-CLAIM-INHERIT")

    assert len(motifs) == 1
    assert len(stories) == 0


@pytest.mark.asyncio
async def test_only_explicit_claim(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # tree-motif has 2 claims, we attach only claim-tree-contextual
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-EXPLICIT-ONE",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed tree motif",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(
                                claim_key="claim-tree-contextual",
                                applicability_note="Applicable note"
                            )
                        ]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    service = CarpetCatalogService(db_session)
    stories = await service.list_carpet_story_associations("CAT-EXPLICIT-ONE")

    assert len(stories) == 1
    assert stories[0].claim_key == "claim-tree-contextual"


@pytest.mark.asyncio
async def test_two_layer_sources(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-TWO-LAYER",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.SOURCE_DOCUMENTED,
                        sources=[CatalogMotifSourceInput(source_key="src-2", locator="p. 100")],
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    service = CarpetCatalogService(db_session)
    stories = await service.list_carpet_story_associations("CAT-TWO-LAYER")

    assert len(stories) == 1
    story = stories[0]

    # Presence source is src-2
    assert len(story.presence_sources) == 1
    assert story.presence_sources[0].source.source_key == "src-2"

    # Claim meaning source is src-1 (from seed claim-star-doc)
    assert len(story.claim_sources) == 1
    assert story.claim_sources[0].source.source_key == "src-1"


@pytest.mark.asyncio
async def test_readiness_states(db_session: AsyncSession):
    service = CarpetCatalogService(db_session)

    # 1. NO_PRIMARY_IMAGE
    c1 = CarpetModel(id=uuid.uuid4(), sku="CAT-R-1", name="No Image", source_type=CarpetSourceType.CATALOG)
    db_session.add(c1)
    await db_session.commit()

    detail1 = await service.get_catalog_carpet_detail("CAT-R-1")
    assert detail1.style_dna_readiness == StyleDnaReadinessEnum.NO_PRIMARY_IMAGE

    # 2. STYLE_DNA_MISSING
    c2 = CarpetModel(id=uuid.uuid4(), sku="CAT-R-2", name="With Image No DNA", source_type=CarpetSourceType.CATALOG)
    db_session.add(c2)
    await db_session.flush()

    img2 = CarpetImageModel(
        id=uuid.uuid4(),
        carpet_id=c2.id,
        original_filename="img2.jpg",
        content_type="image/jpeg",
        storage_key="storage/img2.jpg",
        byte_size=1024,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="sha256_dummy_2",
        is_primary=True
    )
    db_session.add(img2)
    await db_session.commit()

    detail2 = await service.get_catalog_carpet_detail("CAT-R-2")
    assert detail2.style_dna_readiness == StyleDnaReadinessEnum.STYLE_DNA_MISSING

    # 3. STYLE_DNA_COMPLETE
    c3 = CarpetModel(id=uuid.uuid4(), sku="CAT-R-3", name="With Image With DNA", source_type=CarpetSourceType.CATALOG)
    db_session.add(c3)
    await db_session.flush()

    img3 = CarpetImageModel(
        id=uuid.uuid4(),
        carpet_id=c3.id,
        original_filename="img3.jpg",
        content_type="image/jpeg",
        storage_key="storage/img3.jpg",
        byte_size=1024,
        width_px=800,
        height_px=600,
        channels=3,
        sha256="sha256_dummy_3",
        is_primary=True
    )
    db_session.add(img3)
    await db_session.flush()

    profile3 = CarpetStyleProfileModel(
        id=uuid.uuid4(),
        carpet_id=c3.id,
        image_id=img3.id,
        analysis_input_sha256="sha256_dummy_3",
        algorithm_version=STYLE_DNA_ALGORITHM_VERSION,
        status=StyleProfileStatus.COMPLETE,
        analyzed_width_px=800,
        analyzed_height_px=600
    )
    db_session.add(profile3)
    await db_session.commit()

    detail3 = await service.get_catalog_carpet_detail("CAT-R-3")
    assert detail3.style_dna_readiness == StyleDnaReadinessEnum.STYLE_DNA_COMPLETE


@pytest.mark.asyncio
async def test_read_endpoint_no_side_effect(db_session: AsyncSession):
    c = CarpetModel(id=uuid.uuid4(), sku="CAT-SIDE-EFFECT", name="Test Carpet", source_type=CarpetSourceType.CATALOG)
    db_session.add(c)
    await db_session.commit()

    service = CarpetCatalogService(db_session)
    await service.get_catalog_carpet_detail("CAT-SIDE-EFFECT")

    # Verify no CarpetStyleProfileModel was generated
    res = await db_session.execute(select(CarpetStyleProfileModel).where(CarpetStyleProfileModel.carpet_id == c.id))
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_import_dry_run(db_session: AsyncSession):
    dataset = CatalogImportDataset(
        carpets=[CatalogCarpetInput(sku="CAT-DRY", name="Dry Run Carpet")]
    )

    importer = CarpetCatalogImporter(db_session)
    res = await importer.import_dataset(dataset, dry_run=True)
    assert res.dry_run is True
    assert res.carpets_created == 1

    service = CarpetCatalogService(db_session)
    with pytest.raises(CatalogCarpetNotFoundError):
        await service.get_catalog_carpet_detail("CAT-DRY")


@pytest.mark.asyncio
async def test_import_atomicity(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(sku="CAT-ATOMIC-1", name="Valid Carpet 1"),
            CatalogCarpetInput(
                sku="CAT-ATOMIC-2",
                name="Invalid Carpet 2",
                motifs=[
                    # Invalid CURATOR_CONFIRMED without note
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note=None
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    with pytest.raises(CarpetMotifCurationNoteRequiredError):
        await importer.import_dataset(dataset, dry_run=False)

    service = CarpetCatalogService(db_session)
    with pytest.raises(CatalogCarpetNotFoundError):
        await service.get_catalog_carpet_detail("CAT-ATOMIC-1")


@pytest.mark.asyncio
async def test_additive_curation(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset1 = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-ADDITIVE",
                name="Additive Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="First motif"
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    res1 = await importer.import_dataset(dataset1)
    assert res1.carpets_created == 1
    assert res1.motif_associations_created == 1

    dataset2 = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-ADDITIVE",
                name="Additive Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Second motif"
                    )
                ]
            )
        ]
    )

    res2 = await importer.import_dataset(dataset2)
    assert res2.carpets_created == 0
    assert res2.motif_associations_created == 1

    service = CarpetCatalogService(db_session)
    motifs = await service.list_carpet_motifs("CAT-ADDITIVE")
    assert len(motifs) == 2


@pytest.mark.asyncio
async def test_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-API-TEST",
                name="API Catalog Carpet",
                manufacturer="Hereke",
                collection="Classic",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Confirmed star motif",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )

    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    # 1. GET /api/v1/catalog/carpets
    res_list = await client.get("/api/v1/catalog/carpets")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total_count"] == 1
    assert data_list["carpets"][0]["sku"] == "CAT-API-TEST"

    # 2. GET /api/v1/catalog/carpets/{id_or_sku}
    res_detail = await client.get("/api/v1/catalog/carpets/CAT-API-TEST")
    assert res_detail.status_code == 200
    data_detail = res_detail.json()
    assert data_detail["carpet"]["name"] == "API Catalog Carpet"
    assert data_detail["style_dna_readiness"] == "NO_PRIMARY_IMAGE"
    assert data_detail["motif_association_count"] == 1
    assert data_detail["story_association_count"] == 1

    # 3. GET /api/v1/catalog/carpets/{id_or_sku}/motifs
    res_motifs = await client.get("/api/v1/catalog/carpets/CAT-API-TEST/motifs")
    assert res_motifs.status_code == 200
    data_motifs = res_motifs.json()
    assert len(data_motifs) == 1
    assert data_motifs[0]["motif_key"] == "star-motif"

    # 4. GET /api/v1/catalog/carpets/{id_or_sku}/story-associations
    res_stories = await client.get("/api/v1/catalog/carpets/CAT-API-TEST/story-associations")
    assert res_stories.status_code == 200
    data_stories = res_stories.json()
    assert len(data_stories) == 1
    assert data_stories[0]["claim_key"] == "claim-star-doc"
    assert data_stories[0]["themes"] == ["balance_order"]
