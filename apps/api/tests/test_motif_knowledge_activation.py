"""Pytest test suite for POST-v1 A4 Real Source-Backed Motif Knowledge Activation."""
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
    await importer.import_data(schema, dry_run=False)


@pytest.mark.asyncio
async def test_activated_motif_knowledge_counts(db_session: AsyncSession):
    """Verify exact counts for activated motif knowledge entities."""
    s_count = (await db_session.execute(select(func.count(CuratedSourceModel.id)))).scalar()
    m_count = (await db_session.execute(select(func.count(MotifModel.id)))).scalar()
    c_count = (await db_session.execute(select(func.count(MotifStoryClaimModel.id)))).scalar()
    cs_count = (await db_session.execute(select(func.count(MotifStoryClaimSourceModel.id)))).scalar()
    ct_count = (await db_session.execute(select(func.count(MotifStoryClaimThemeModel.id)))).scalar()

    assert s_count == 6
    assert m_count == 13
    assert c_count == 12
    assert cs_count == 19
    assert ct_count == 21


@pytest.mark.asyncio
async def test_claim_status_invariants(db_session: AsyncSession):
    """Verify strict status invariants across all activated claims."""
    res = await db_session.execute(select(MotifStoryClaimModel))
    claims = res.scalars().all()

    for c in claims:
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


@pytest.mark.asyncio
async def test_neutral_motif_descriptions(db_session: AsyncSession):
    """Verify motifs contain visual descriptions only and no symbolism/meaning attributes."""
    res = await db_session.execute(select(MotifModel))
    motifs = res.scalars().all()

    for m in motifs:
        assert m.name_tr
        assert m.visual_description_tr
        # Ensure no story/meaning columns exist on MotifModel
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

    # Ensure all 8 canonical themes are represented in activated dataset
    assert len(used_keys) == 8


@pytest.mark.asyncio
async def test_catalog_and_boundary_immutability(db_session: AsyncSession):
    """Verify Catalog baseline, images, Style DNA, and A5/A6/A7 association tables in production DB."""
    motif_assoc_c = (await db_session.execute(
        select(func.count(CarpetMotifAssociationModel.id))
    )).scalar()

    story_assoc_c = (await db_session.execute(
        select(func.count(CarpetStoryAssociationModel.id))
    )).scalar()

    # Boundary checks: A5 associations must NOT exist in A4!
    assert motif_assoc_c == 0
    assert story_assoc_c == 0

    # Production DB File Baselines
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        carpets = cur.execute("SELECT COUNT(*) FROM carpets WHERE source_type = 'CATALOG'").fetchone()[0]
        images = cur.execute("SELECT COUNT(*) FROM carpet_images WHERE is_primary = 1").fetchone()[0]
        styles = cur.execute("SELECT COUNT(*) FROM carpet_style_profiles").fetchone()[0]
        conn.close()

        assert carpets == 232, f"Expected 232 catalog products, got {carpets}"
        assert images == 227, f"Expected 227 primary images, got {images}"
        assert styles == 227, f"Expected 227 style profiles, got {styles}"

