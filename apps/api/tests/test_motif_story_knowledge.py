"""Comprehensive Pytest test suite for Curated Motif Story + Source Provenance v1."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.motif_knowledge import (
    CuratedSourceModel,
    MotifModel,
    MotifStoryClaimModel,
    SourceTypeEnum,
    MotifStoryStatusEnum,
)
from app.domain.motif_knowledge.constants import CURATION_SCHEMA_VERSION, MOTIF_STORY_KNOWLEDGE_VERSION
from app.domain.motif_knowledge.exceptions import (
    CurationValidationError,
    CurationConflictError,
    UnsupportedSchemaVersionError,
    MotifNotFoundError,
    ClaimNotFoundError,
    SourceNotFoundError,
)
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import (
    CurationImportSchema,
    SourceImportItem,
    MotifImportItem,
    ClaimImportItem,
    ClaimSourceLinkImportItem,
)
from app.domain.motif_knowledge.service import MotifKnowledgeService


@pytest.mark.asyncio
async def test_source_model(db_session: AsyncSession):
    src = CuratedSourceModel(
        source_key="met-carpet-catalog-1998",
        source_type=SourceTypeEnum.MUSEUM_CATALOG,
        title="Metropolitan Museum Oriental Rug Collection",
        citation_text="Metropolitan Museum of Art. Oriental Rugs in the Metropolitan Museum. New York, 1998."
    )
    db_session.add(src)
    await db_session.commit()

    res = await db_session.execute(select(CuratedSourceModel).where(CuratedSourceModel.source_key == "met-carpet-catalog-1998"))
    fetched = res.scalar_one()
    assert fetched.title == "Metropolitan Museum Oriental Rug Collection"
    assert fetched.source_type == SourceTypeEnum.MUSEUM_CATALOG


@pytest.mark.asyncio
async def test_motif_model_neutral_description(db_session: AsyncSession):
    motif = MotifModel(
        motif_key="eight-point-star",
        name_tr="Sekiz Köşeli Yıldız",
        name_en="Eight-Pointed Star",
        visual_description_tr="Merkezden yayılan sekiz geometrik kol."
    )
    db_session.add(motif)
    await db_session.commit()

    # Ensure no story/meaning columns exist on MotifModel
    assert not hasattr(motif, "meaning")
    assert not hasattr(motif, "story")
    assert not hasattr(motif, "symbolism")
    assert not hasattr(motif, "narrative_theme")


@pytest.mark.asyncio
async def test_documented_status_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[
            SourceImportItem(
                source_key="src-1",
                title="Source One",
                citation_text="Citation 1"
            )
        ],
        motifs=[
            MotifImportItem(
                motif_key="motif-star",
                name_tr="Yıldız Motif"
            )
        ],
        claims=[
            ClaimImportItem(
                claim_key="claim-star-doc",
                motif_key="motif-star",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Bu motif gökyüzü düzenini simgeler.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["balance_order"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema, dry_run=False)
    assert res.claims_created == 1


@pytest.mark.asyncio
async def test_documented_without_source_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        motifs=[MotifImportItem(motif_key="motif-star", name_tr="Yıldız")],
        claims=[
            ClaimImportItem(
                claim_key="claim-star-no-src",
                motif_key="motif-star",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Unbacked claim text.",
                source_links=[]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "at least 1 source link" in str(exc.value)


@pytest.mark.asyncio
async def test_contextual_status_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-context", title="Context Source", citation_text="Cit Context")],
        motifs=[MotifImportItem(motif_key="motif-tree", name_tr="Hayat Ağacı")],
        claims=[
            ClaimImportItem(
                claim_key="claim-tree-contextual",
                motif_key="motif-tree",
                status=MotifStoryStatusEnum.CONTEXTUAL,
                claim_text_tr="19. yüzyıl İç Anadolu dokumalarında soy bağını ifade eder.",
                context_note="19. yüzyıl İç Anadolu yöresel dokuma gelenekleri.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-context")],
                theme_keys=["continuity_connection"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema)
    assert res.claims_created == 1


@pytest.mark.asyncio
async def test_contextual_without_context_note_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-c", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-tree", name_tr="Tree")],
        claims=[
            ClaimImportItem(
                claim_key="claim-tree-no-context-note",
                motif_key="motif-tree",
                status=MotifStoryStatusEnum.CONTEXTUAL,
                claim_text_tr="Text",
                context_note=None,
                source_links=[ClaimSourceLinkImportItem(source_key="src-c")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "requires non-empty context_note" in str(exc.value)


@pytest.mark.asyncio
async def test_contested_status_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[
            SourceImportItem(source_key="src-contest-1", title="Author A", citation_text="Cit A"),
            SourceImportItem(source_key="src-contest-2", title="Author B", citation_text="Cit B")
        ],
        motifs=[MotifImportItem(motif_key="motif-ram", name_tr="Koçboynuzu")],
        claims=[
            ClaimImportItem(
                claim_key="claim-ram-contested",
                motif_key="motif-ram",
                status=MotifStoryStatusEnum.CONTESTED,
                claim_text_tr="Güç veya bereketi simgelediği yönünde farklı görüşler mevcuttur.",
                contest_note="A yazarı güç sembolü, B yazarı ise mevsimsel bereket sembolü kabul eder.",
                source_links=[
                    ClaimSourceLinkImportItem(source_key="src-contest-1"),
                    ClaimSourceLinkImportItem(source_key="src-contest-2")
                ],
                theme_keys=["tradition_craft"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema)
    assert res.claims_created == 1


@pytest.mark.asyncio
async def test_contested_one_source_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-single", title="Title", citation_text="Cit")],
        motifs=[MotifImportItem(motif_key="motif-ram", name_tr="Koçboynuzu")],
        claims=[
            ClaimImportItem(
                claim_key="claim-ram-one-src",
                motif_key="motif-ram",
                status=MotifStoryStatusEnum.CONTESTED,
                claim_text_tr="Contested claim",
                contest_note="Contest note",
                source_links=[ClaimSourceLinkImportItem(source_key="src-single")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "requires at least 2 distinct source links" in str(exc.value)


@pytest.mark.asyncio
async def test_unknown_status_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-unk", title="Title", citation_text="Cit")],
        motifs=[MotifImportItem(motif_key="motif-mystery", name_tr="Bilinmeyen Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-mystery-unknown",
                motif_key="motif-mystery",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr=None,
                uncertainty_note="Akademik literatürde bu motif için doğrulanmış anlatı bulunmamaktadır.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-unk")],
                theme_keys=[]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema)
    assert res.claims_created == 1


@pytest.mark.asyncio
async def test_unknown_with_story_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        motifs=[MotifImportItem(motif_key="motif-mystery", name_tr="Bilinmeyen Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-mystery-invalid-story",
                motif_key="motif-mystery",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr="Invented story text for unknown status",
                theme_keys=[]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "UNKNOWN claim" in str(exc.value) and "must have claim_text_tr set to None/null" in str(exc.value)


@pytest.mark.asyncio
async def test_unknown_with_theme_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        motifs=[MotifImportItem(motif_key="motif-mystery", name_tr="Bilinmeyen Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-mystery-invalid-theme",
                motif_key="motif-mystery",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr=None,
                theme_keys=["nature_growth"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "UNKNOWN claim" in str(exc.value) and "must not have theme links" in str(exc.value)


@pytest.mark.asyncio
async def test_claim_without_theme_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-notheme", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-hook", name_tr="Çengel")],
        claims=[
            ClaimImportItem(
                claim_key="claim-hook-notheme",
                motif_key="motif-hook",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Dokumada kenar sabitleyici geometrik unsur.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-notheme")],
                theme_keys=[]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema)
    assert res.claims_created == 1


@pytest.mark.asyncio
async def test_multiple_themes_valid(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-multitheme", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-water", name_tr="Akar Su")],
        claims=[
            ClaimImportItem(
                claim_key="claim-water-multi",
                motif_key="motif-water",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yaşam kaynağı ve kültürel süreklilik simgesi.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-multitheme")],
                theme_keys=["nature_growth", "cultural_heritage", "continuity_connection"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res = await importer.import_data(schema)
    assert res.claim_themes_created == 3


@pytest.mark.asyncio
async def test_unknown_theme_key_rejected(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-x", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-x", name_tr="X")],
        claims=[
            ClaimImportItem(
                claim_key="claim-bad-theme",
                motif_key="motif-x",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Valid text",
                source_links=[ClaimSourceLinkImportItem(source_key="src-x")],
                theme_keys=["invalid_non_canonical_theme"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError) as exc:
        await importer.import_data(schema)
    assert "unknown narrative theme_key" in str(exc.value)


@pytest.mark.asyncio
async def test_absence_vs_unknown_distinct(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-abs", title="T", citation_text="C")],
        motifs=[
            MotifImportItem(motif_key="motif-a-noclaim", name_tr="Motif A"),
            MotifImportItem(motif_key="motif-b-unknown", name_tr="Motif B")
        ],
        claims=[
            ClaimImportItem(
                claim_key="claim-b-unknown",
                motif_key="motif-b-unknown",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr=None,
                source_links=[ClaimSourceLinkImportItem(source_key="src-abs")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema)

    service = MotifKnowledgeService(db_session)
    motif_a = await service.get_motif("motif-a-noclaim")
    motif_b = await service.get_motif("motif-b-unknown")

    assert len(motif_a.story_claims) == 0
    assert len(motif_b.story_claims) == 1
    assert motif_b.story_claims[0].status == MotifStoryStatusEnum.UNKNOWN


@pytest.mark.asyncio
async def test_import_dry_run(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-dry", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-dry", name_tr="Dry Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-dry",
                motif_key="motif-dry",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Dry text",
                source_links=[ClaimSourceLinkImportItem(source_key="src-dry")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    dry_res = await importer.import_data(schema, dry_run=True)
    assert dry_res.dry_run is True
    assert dry_res.claims_created == 1

    # Verify no records written to DB
    service = MotifKnowledgeService(db_session)
    with pytest.raises(MotifNotFoundError):
        await service.get_motif("motif-dry")


@pytest.mark.asyncio
async def test_atomic_import_rollback(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-valid", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-atomic", name_tr="Atomic Motif")],
        claims=[
            # Valid claim
            ClaimImportItem(
                claim_key="claim-1-ok",
                motif_key="motif-atomic",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Ok text",
                source_links=[ClaimSourceLinkImportItem(source_key="src-valid")]
            ),
            # Invalid claim (DOCUMENTED without source)
            ClaimImportItem(
                claim_key="claim-2-fail",
                motif_key="motif-atomic",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Fail text",
                source_links=[]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    with pytest.raises(CurationValidationError):
        await importer.import_data(schema, dry_run=False)

    # Verify 0 records persisted
    service = MotifKnowledgeService(db_session)
    with pytest.raises(MotifNotFoundError):
        await service.get_motif("motif-atomic")


@pytest.mark.asyncio
async def test_idempotent_import(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="src-idem", title="T", citation_text="C")],
        motifs=[MotifImportItem(motif_key="motif-idem", name_tr="Idem Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-idem",
                motif_key="motif-idem",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Idem text",
                source_links=[ClaimSourceLinkImportItem(source_key="src-idem")]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    res1 = await importer.import_data(schema, dry_run=False)
    assert res1.claims_created == 1

    # Second run with exact same dataset
    res2 = await importer.import_data(schema, dry_run=False)
    assert res2.claims_created == 0
    assert res2.motifs_created == 0
    assert res2.sources_created == 0


@pytest.mark.asyncio
async def test_curation_conflict_rejected(db_session: AsyncSession):
    schema1 = CurationImportSchema(
        motifs=[MotifImportItem(motif_key="motif-conf", name_tr="Original Name")]
    )

    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema1)

    schema2 = CurationImportSchema(
        motifs=[MotifImportItem(motif_key="motif-conf", name_tr="Conflicting Name")]
    )

    with pytest.raises(CurationConflictError) as exc:
        await importer.import_data(schema2)
    assert "Motif key conflict" in str(exc.value)


@pytest.mark.asyncio
async def test_read_order(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[
            SourceImportItem(source_key="src-z-catalog", title="Catalog Z", citation_text="Cit Z"),
            SourceImportItem(source_key="src-a-book", title="Book A", citation_text="Cit A")
        ],
        motifs=[MotifImportItem(motif_key="motif-order", name_tr="Order Motif")],
        claims=[
            ClaimImportItem(
                claim_key="claim-order",
                motif_key="motif-order",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Order test claim",
                source_links=[
                    ClaimSourceLinkImportItem(source_key="src-z-catalog"),
                    ClaimSourceLinkImportItem(source_key="src-a-book")
                ],
                # Pass themes out of canonical order
                theme_keys=["cultural_heritage", "nature_growth", "balance_order"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema)

    service = MotifKnowledgeService(db_session)
    claim = await service.get_claim("claim-order")

    # Themes must be ordered N1..N8: nature_growth -> balance_order -> cultural_heritage
    assert claim.themes == ["nature_growth", "balance_order", "cultural_heritage"]

    # Sources must be ordered by source_key ASC: src-a-book -> src-z-catalog
    assert claim.sources[0].source.source_key == "src-a-book"
    assert claim.sources[1].source.source_key == "src-z-catalog"


@pytest.mark.asyncio
async def test_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[SourceImportItem(source_key="met-src-1", title="Met Title", citation_text="Met Citation")],
        motifs=[MotifImportItem(motif_key="lotus-flower", name_tr="Lotus Çiçeği", name_en="Lotus Flower")],
        claims=[
            ClaimImportItem(
                claim_key="claim-lotus-rebirth",
                motif_key="lotus-flower",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yeniden doğuş simgesi.",
                source_links=[ClaimSourceLinkImportItem(source_key="met-src-1")],
                theme_keys=["renewal_transformation"]
            )
        ]
    )

    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema)

    # 1. GET /api/v1/motifs
    res_motifs = await client.get("/api/v1/motifs")
    assert res_motifs.status_code == 200
    data_motifs = res_motifs.json()
    assert data_motifs["total_count"] == 1
    assert data_motifs["motifs"][0]["motif_key"] == "lotus-flower"

    # 2. GET /api/v1/motifs/{id_or_key}
    res_m = await client.get("/api/v1/motifs/lotus-flower")
    assert res_m.status_code == 200
    data_m = res_m.json()
    assert data_m["name_tr"] == "Lotus Çiçeği"

    # 3. GET /api/v1/motif-story-claims
    res_claims = await client.get("/api/v1/motif-story-claims")
    assert res_claims.status_code == 200
    data_c = res_claims.json()
    assert data_c["total_count"] == 1
    assert data_c["claims"][0]["claim_key"] == "claim-lotus-rebirth"

    # 4. GET /api/v1/motif-story-claims/{id_or_key}
    res_c = await client.get("/api/v1/motif-story-claims/claim-lotus-rebirth")
    assert res_c.status_code == 200
    assert res_c.json()["status"] == "DOCUMENTED"

    # 5. GET /api/v1/sources/{id_or_key}
    res_s = await client.get("/api/v1/sources/met-src-1")
    assert res_s.status_code == 200
    assert res_s.json()["title"] == "Met Title"
