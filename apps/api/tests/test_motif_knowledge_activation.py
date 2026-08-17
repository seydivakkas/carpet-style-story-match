"""Pytest test suite for POST-v1 A4A Claim ↔ Source Provenance Reconciliation."""
import json
from pathlib import Path
import sqlite3
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models.motif_knowledge import (
    CuratedSourceModel,
    MotifModel,
    MotifStoryClaimModel,
    MotifStoryClaimSourceModel,
    MotifStoryClaimThemeModel,
    MotifStoryStatusEnum,
    SourceTypeEnum,
)
from app.db.models.carpet_story_association import CarpetMotifAssociationModel, CarpetStoryAssociationModel
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import CurationImportSchema

DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "activation" / "motif_knowledge" / "motif-knowledge.json"


@pytest.fixture(autouse=True)
async def seed_motif_knowledge(db_session: AsyncSession):
    """Seed in-memory test DB session with activated motif-knowledge dataset."""
    assert DATASET_PATH.exists(), f"Motif knowledge dataset file missing at {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    schema = CurationImportSchema.model_validate(raw_data)
    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema, dry_run=False, allow_overwrite=True)


@pytest.mark.asyncio
async def test_reconciled_motif_knowledge_counts(db_session: AsyncSession):
    """Verify exact reconciled counts for activated motif knowledge entities (A4A)."""
    s_count = (await db_session.execute(select(func.count(CuratedSourceModel.id)))).scalar()
    m_count = (await db_session.execute(select(func.count(MotifModel.id)))).scalar()
    c_count = (await db_session.execute(select(func.count(MotifStoryClaimModel.id)))).scalar()
    cs_count = (await db_session.execute(select(func.count(MotifStoryClaimSourceModel.id)))).scalar()
    ct_count = (await db_session.execute(select(func.count(MotifStoryClaimThemeModel.id)))).scalar()

    assert s_count == 6
    assert m_count == 13
    assert c_count == 12
    assert cs_count == 20
    assert ct_count == 21


@pytest.mark.asyncio
async def test_source_identity_separation_and_ellis_resolution(db_session: AsyncSession):
    """Verify separation of MUSEUM_OBJECT from MUSEUM_CATALOG and resolution of Ellis (1988)."""
    res_obj = await db_session.execute(
        select(CuratedSourceModel).where(CuratedSourceModel.source_key == "met-museum-safavid-medallion-carpet-14104")
    )
    src_obj = res_obj.scalar_one()
    assert src_obj.source_type == SourceTypeEnum.MUSEUM_OBJECT
    assert "14.40.714" in src_obj.title or "14.40.714" in src_obj.citation_text

    res_ellis = await db_session.execute(
        select(CuratedSourceModel).where(CuratedSourceModel.source_key == "met-museum-oriental-rug-catalog-1988")
    )
    src_ellis = res_ellis.scalar_one()
    assert src_ellis.source_type == SourceTypeEnum.MUSEUM_CATALOG
    assert "Ellis" in src_ellis.citation_text
    assert src_ellis.isbn == "0-87099-522-8"

    # Verify they are separate primary key records
    assert src_obj.id != src_ellis.id


@pytest.mark.asyncio
async def test_claim_status_invariants_and_downgrade(db_session: AsyncSession):
    """Verify strict status invariants and check downgraded lotus claim."""
    res = await db_session.execute(select(MotifStoryClaimModel))
    claims = res.scalars().all()

    status_counts = {}
    for c in claims:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1

        res_src = await db_session.execute(
            select(MotifStoryClaimSourceModel).where(MotifStoryClaimSourceModel.claim_id == c.id)
        )
        sources = res_src.scalars().all()

        res_thm = await db_session.execute(
            select(MotifStoryClaimThemeModel).where(MotifStoryClaimThemeModel.claim_id == c.id)
        )
        themes = res_thm.scalars().all()

        if c.status == MotifStoryStatusEnum.DOCUMENTED:
            assert c.claim_text_tr and c.claim_text_tr.strip()
            assert len(sources) >= 1

        elif c.status == MotifStoryStatusEnum.CONTEXTUAL:
            assert c.claim_text_tr and c.claim_text_tr.strip()
            assert c.context_note and c.context_note.strip()
            assert len(sources) >= 1

        elif c.status == MotifStoryStatusEnum.CONTESTED:
            assert c.claim_text_tr and c.claim_text_tr.strip()
            assert c.contest_note and c.contest_note.strip()
            distinct_source_ids = {s.source_id for s in sources}
            assert len(distinct_source_ids) >= 2

        elif c.status == MotifStoryStatusEnum.UNKNOWN:
            assert c.claim_text_tr is None
            assert c.claim_text_en is None
            assert len(themes) == 0
            assert c.uncertainty_note and c.uncertainty_note.strip()

    # Reconciled status counts check
    assert status_counts[MotifStoryStatusEnum.DOCUMENTED] == 6
    assert status_counts[MotifStoryStatusEnum.CONTEXTUAL] == 3
    assert status_counts[MotifStoryStatusEnum.CONTESTED] == 2
    assert status_counts[MotifStoryStatusEnum.UNKNOWN] == 1

    # Verify lotus claim was downgraded to CONTEXTUAL
    res_lotus = await db_session.execute(
        select(MotifStoryClaimModel).where(MotifStoryClaimModel.claim_key == "claim-lotus-rebirth")
    )
    c_lotus = res_lotus.scalar_one()
    assert c_lotus.status == MotifStoryStatusEnum.CONTEXTUAL
    assert c_lotus.context_note and "İslam halı sanatında" in c_lotus.context_note


@pytest.mark.asyncio
async def test_locators_and_evidence_notes(db_session: AsyncSession):
    """Verify every claim-source link contains non-empty locator and evidence note."""
    res_links = await db_session.execute(select(MotifStoryClaimSourceModel))
    links = res_links.scalars().all()

    assert len(links) == 20
    for link in links:
        assert link.locator and link.locator.strip(), f"Missing locator for link {link.id}"
        assert link.source_note and link.source_note.strip(), f"Missing evidence note for link {link.id}"


@pytest.mark.asyncio
async def test_neutral_motif_descriptions(db_session: AsyncSession):
    """Verify motifs contain visual descriptions only and no symbolism/meaning attributes."""
    res = await db_session.execute(select(MotifModel))
    motifs = res.scalars().all()

    for m in motifs:
        assert m.name_tr
        assert m.visual_description_tr
        assert not hasattr(m, "meaning")
        assert not hasattr(m, "story")
        assert not hasattr(m, "symbolism")
        assert not hasattr(m, "narrative_theme")


@pytest.mark.asyncio
async def test_canonical_narrative_themes_only(db_session: AsyncSession):
    """Verify all claim theme links strictly match canonical narrative theme keys (N1..N8)."""
    canonical_keys = {t["key"] for t in CANONICAL_NARRATIVE_THEMES}
    res = await db_session.execute(select(MotifStoryClaimThemeModel.theme_key))
    used_keys = set(res.scalars().all())

    for k in used_keys:
        assert k in canonical_keys

    assert len(used_keys) == 8


@pytest.mark.asyncio
async def test_importer_idempotency_second_run(db_session: AsyncSession):
    """Verify second import of exact dataset creates 0 new records."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    schema = CurationImportSchema.model_validate(raw_data)
    importer = MotifKnowledgeImporter(db_session)
    res_second = await importer.import_data(schema, dry_run=False, allow_overwrite=False)

    assert res_second.sources_created == 0
    assert res_second.motifs_created == 0
    assert res_second.claims_created == 0
    assert res_second.claim_sources_created == 0
    assert res_second.claim_themes_created == 0


@pytest.mark.asyncio
async def test_catalog_and_boundary_immutability(db_session: AsyncSession):
    """Verify Catalog baseline, images, Style DNA, and A5/A6/A7 association tables in production DB."""
    motif_assoc_c = (await db_session.execute(
        select(func.count(CarpetMotifAssociationModel.id))
    )).scalar()

    story_assoc_c = (await db_session.execute(
        select(func.count(CarpetStoryAssociationModel.id))
    )).scalar()

    assert motif_assoc_c == 0
    assert story_assoc_c == 0

    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if Path(db_path).exists():
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            carpets = cur.execute("SELECT COUNT(*) FROM carpets WHERE source_type = 'CATALOG'").fetchone()[0]
            images = cur.execute("SELECT COUNT(*) FROM carpet_images ci JOIN carpets c ON ci.carpet_id = c.id WHERE c.source_type = 'CATALOG' AND ci.is_primary = 1").fetchone()[0]
            styles = cur.execute("SELECT COUNT(*) FROM carpet_style_profiles csp JOIN carpets c ON csp.carpet_id = c.id WHERE c.source_type = 'CATALOG'").fetchone()[0]
            conn.close()

            if carpets == 0:
                pytest.skip("Baseline SQLite carpet.db is not initialized in current test environment.")

            assert carpets == 232, f"Expected 232 catalog products, got {carpets}"
            assert images == 227, f"Expected 227 primary images, got {images}"
            assert styles == 227, f"Expected 227 style profiles, got {styles}"
        except sqlite3.OperationalError:
            pytest.skip("Baseline SQLite carpet.db is not initialized in current test environment.")


