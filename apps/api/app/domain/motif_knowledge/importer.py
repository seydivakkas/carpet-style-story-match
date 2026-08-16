"""MotifKnowledgeImporter for Curated Motif Story + Source Provenance v1."""
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.motif_knowledge import (
    CuratedSourceModel,
    MotifModel,
    MotifStoryClaimModel,
    MotifStoryClaimSourceModel,
    MotifStoryClaimThemeModel,
    MotifStoryStatusEnum,
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.motif_knowledge.constants import (
    MOTIF_STORY_KNOWLEDGE_VERSION,
    CURATION_SCHEMA_VERSION,
)
from app.domain.motif_knowledge.exceptions import (
    CurationValidationError,
    CurationConflictError,
    UnsupportedSchemaVersionError,
)
from app.domain.motif_knowledge.schemas import CurationImportSchema


@dataclass(frozen=True)
class ImportResult:
    dry_run: bool
    sources_created: int
    motifs_created: int
    claims_created: int
    claim_sources_created: int
    claim_themes_created: int


class MotifKnowledgeImporter:
    """Deterministic importer for motif knowledge with strict validation and dry-run support."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_data(
        self,
        import_schema: CurationImportSchema,
        dry_run: bool = False,
        allow_overwrite: bool = False
    ) -> ImportResult:
        # 1. Schema version check
        if import_schema.schema_version != CURATION_SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Unsupported schema_version: {import_schema.schema_version}. Expected: {CURATION_SCHEMA_VERSION}"
            )

        # 2. Check input array internal duplicates
        source_keys_in_input = [s.source_key for s in import_schema.sources]
        if len(source_keys_in_input) != len(set(source_keys_in_input)):
            raise CurationValidationError("Duplicate source_key found in input sources")

        motif_keys_in_input = [m.motif_key for m in import_schema.motifs]
        if len(motif_keys_in_input) != len(set(motif_keys_in_input)):
            raise CurationValidationError("Duplicate motif_key found in input motifs")

        claim_keys_in_input = [c.claim_key for c in import_schema.claims]
        if len(claim_keys_in_input) != len(set(claim_keys_in_input)):
            raise CurationValidationError("Duplicate claim_key found in input claims")

        # Fetch existing keys from DB
        existing_sources = await self._get_existing_sources()
        existing_motifs = await self._get_existing_motifs()
        existing_claims = await self._get_existing_claims()

        available_source_keys: Set[str] = set(existing_sources.keys()).union(set(source_keys_in_input))
        available_motif_keys: Set[str] = set(existing_motifs.keys()).union(set(motif_keys_in_input))

        # Check content conflicts on existing DB records unless allow_overwrite is True
        if not allow_overwrite:
            for s_item in import_schema.sources:
                if s_item.source_key in existing_sources:
                    ex = existing_sources[s_item.source_key]
                    if ex.title != s_item.title or ex.citation_text != s_item.citation_text or ex.source_type != s_item.source_type:
                        raise CurationConflictError(
                            f"Source key conflict for '{s_item.source_key}': content does not match existing DB record"
                        )

            for m_item in import_schema.motifs:
                if m_item.motif_key in existing_motifs:
                    ex = existing_motifs[m_item.motif_key]
                    if ex.name_tr != m_item.name_tr:
                        raise CurationConflictError(
                            f"Motif key conflict for '{m_item.motif_key}': content does not match existing DB record"
                        )

        canonical_theme_set = {t["key"] for t in CANONICAL_NARRATIVE_THEMES}

        # 3. Validate claims & status invariants
        for c_item in import_schema.claims:
            if not allow_overwrite and c_item.claim_key in existing_claims:
                ex = existing_claims[c_item.claim_key]
                if ex.status != c_item.status or ex.claim_text_tr != c_item.claim_text_tr:
                    raise CurationConflictError(
                        f"Claim key conflict for '{c_item.claim_key}': content does not match existing DB record"
                    )

            if c_item.motif_key not in available_motif_keys:
                raise CurationValidationError(
                    f"Claim '{c_item.claim_key}' references unknown motif_key: '{c_item.motif_key}'"
                )

            # Check theme keys
            for t_key in c_item.theme_keys:
                if t_key not in canonical_theme_set:
                    raise CurationValidationError(
                        f"Claim '{c_item.claim_key}' references unknown narrative theme_key: '{t_key}'"
                    )

            # Check source keys
            linked_source_keys = [sl.source_key for sl in c_item.source_links]
            if len(linked_source_keys) != len(set(linked_source_keys)):
                raise CurationValidationError(
                    f"Claim '{c_item.claim_key}' has duplicate source_key in source_links"
                )

            for sl in c_item.source_links:
                if sl.source_key not in available_source_keys:
                    raise CurationValidationError(
                        f"Claim '{c_item.claim_key}' references unknown source_key: '{sl.source_key}'"
                    )

            # Validate Status Invariants
            st = c_item.status
            if st == MotifStoryStatusEnum.DOCUMENTED:
                if not c_item.claim_text_tr or not c_item.claim_text_tr.strip():
                    raise CurationValidationError(
                        f"DOCUMENTED claim '{c_item.claim_key}' requires non-empty claim_text_tr"
                    )
                if len(c_item.source_links) < 1:
                    raise CurationValidationError(
                        f"DOCUMENTED claim '{c_item.claim_key}' requires at least 1 source link"
                    )

            elif st == MotifStoryStatusEnum.CONTEXTUAL:
                if not c_item.claim_text_tr or not c_item.claim_text_tr.strip():
                    raise CurationValidationError(
                        f"CONTEXTUAL claim '{c_item.claim_key}' requires non-empty claim_text_tr"
                    )
                if not c_item.context_note or not c_item.context_note.strip():
                    raise CurationValidationError(
                        f"CONTEXTUAL claim '{c_item.claim_key}' requires non-empty context_note"
                    )
                if len(c_item.source_links) < 1:
                    raise CurationValidationError(
                        f"CONTEXTUAL claim '{c_item.claim_key}' requires at least 1 source link"
                    )

            elif st == MotifStoryStatusEnum.CONTESTED:
                if not c_item.claim_text_tr or not c_item.claim_text_tr.strip():
                    raise CurationValidationError(
                        f"CONTESTED claim '{c_item.claim_key}' requires non-empty claim_text_tr"
                    )
                if not c_item.contest_note or not c_item.contest_note.strip():
                    raise CurationValidationError(
                        f"CONTESTED claim '{c_item.claim_key}' requires non-empty contest_note"
                    )
                if len(set(linked_source_keys)) < 2:
                    raise CurationValidationError(
                        f"CONTESTED claim '{c_item.claim_key}' requires at least 2 distinct source links"
                    )

            elif st == MotifStoryStatusEnum.UNKNOWN:
                if c_item.claim_text_tr is not None and c_item.claim_text_tr.strip():
                    raise CurationValidationError(
                        f"UNKNOWN claim '{c_item.claim_key}' must have claim_text_tr set to None/null"
                    )
                if len(c_item.theme_keys) > 0:
                    raise CurationValidationError(
                        f"UNKNOWN claim '{c_item.claim_key}' must not have theme links (theme_keys must be empty)"
                    )

        if dry_run:
            sources_to_create = sum(1 for s in import_schema.sources if s.source_key not in existing_sources)
            motifs_to_create = sum(1 for m in import_schema.motifs if m.motif_key not in existing_motifs)
            claims_to_create = sum(1 for c in import_schema.claims if c.claim_key not in existing_claims)

            claim_sources_to_create = 0
            claim_themes_to_create = 0
            for c in import_schema.claims:
                claim_sources_to_create += len(c.source_links)
                claim_themes_to_create += len(c.theme_keys)

            return ImportResult(
                dry_run=True,
                sources_created=sources_to_create,
                motifs_created=motifs_to_create,
                claims_created=claims_to_create,
                claim_sources_created=claim_sources_to_create,
                claim_themes_created=claim_themes_to_create
            )

        # 4. Atomic Execution Phase
        sources_created_count = 0
        motifs_created_count = 0
        claims_created_count = 0
        claim_sources_created_count = 0
        claim_themes_created_count = 0

        source_model_map: Dict[str, CuratedSourceModel] = dict(existing_sources)
        motif_model_map: Dict[str, MotifModel] = dict(existing_motifs)

        # Create/Update sources
        for s_item in import_schema.sources:
            if s_item.source_key not in source_model_map:
                s_model = CuratedSourceModel(
                    id=uuid.uuid4(),
                    source_key=s_item.source_key,
                    source_type=s_item.source_type,
                    title=s_item.title,
                    citation_text=s_item.citation_text,
                    creator_or_institution=s_item.creator_or_institution,
                    publication_year=s_item.publication_year,
                    url=s_item.url,
                    doi=s_item.doi,
                    isbn=s_item.isbn,
                    rights_note=s_item.rights_note
                )
                self.session.add(s_model)
                source_model_map[s_item.source_key] = s_model
                sources_created_count += 1
            elif allow_overwrite:
                s_model = source_model_map[s_item.source_key]
                s_model.source_type = s_item.source_type
                s_model.title = s_item.title
                s_model.citation_text = s_item.citation_text
                s_model.creator_or_institution = s_item.creator_or_institution
                s_model.publication_year = s_item.publication_year
                s_model.url = s_item.url
                s_model.doi = s_item.doi
                s_model.isbn = s_item.isbn
                s_model.rights_note = s_item.rights_note

        # Create/Update motifs
        for m_item in import_schema.motifs:
            if m_item.motif_key not in motif_model_map:
                m_model = MotifModel(
                    id=uuid.uuid4(),
                    motif_key=m_item.motif_key,
                    name_tr=m_item.name_tr,
                    name_en=m_item.name_en,
                    visual_description_tr=m_item.visual_description_tr,
                    visual_description_en=m_item.visual_description_en
                )
                self.session.add(m_model)
                motif_model_map[m_item.motif_key] = m_model
                motifs_created_count += 1
            elif allow_overwrite:
                m_model = motif_model_map[m_item.motif_key]
                m_model.name_tr = m_item.name_tr
                m_model.name_en = m_item.name_en
                m_model.visual_description_tr = m_item.visual_description_tr
                m_model.visual_description_en = m_item.visual_description_en

        await self.session.flush()

        # Create/Update claims
        for c_item in import_schema.claims:
            if c_item.claim_key not in existing_claims:
                motif_obj = motif_model_map[c_item.motif_key]
                c_model = MotifStoryClaimModel(
                    id=uuid.uuid4(),
                    claim_key=c_item.claim_key,
                    motif_id=motif_obj.id,
                    status=c_item.status,
                    claim_text_tr=c_item.claim_text_tr,
                    claim_text_en=c_item.claim_text_en,
                    context_note=c_item.context_note,
                    contest_note=c_item.contest_note,
                    uncertainty_note=c_item.uncertainty_note,
                    knowledge_version=MOTIF_STORY_KNOWLEDGE_VERSION
                )
                self.session.add(c_model)
                claims_created_count += 1

                for sl in c_item.source_links:
                    src_obj = source_model_map[sl.source_key]
                    cs_link = MotifStoryClaimSourceModel(
                        id=uuid.uuid4(),
                        claim_id=c_model.id,
                        source_id=src_obj.id,
                        locator=sl.locator,
                        source_note=sl.source_note
                    )
                    self.session.add(cs_link)
                    claim_sources_created_count += 1

                for t_key in c_item.theme_keys:
                    ct_link = MotifStoryClaimThemeModel(
                        id=uuid.uuid4(),
                        claim_id=c_model.id,
                        theme_key=t_key
                    )
                    self.session.add(ct_link)
                    claim_themes_created_count += 1

            elif allow_overwrite:
                c_model = existing_claims[c_item.claim_key]
                c_model.status = c_item.status
                c_model.claim_text_tr = c_item.claim_text_tr
                c_model.claim_text_en = c_item.claim_text_en
                c_model.context_note = c_item.context_note
                c_model.contest_note = c_item.contest_note
                c_model.uncertainty_note = c_item.uncertainty_note

                # Delete existing child links for this claim to re-link updated sources/themes
                res_sl = await self.session.execute(
                    select(MotifStoryClaimSourceModel).where(MotifStoryClaimSourceModel.claim_id == c_model.id)
                )
                for sl_obj in res_sl.scalars().all():
                    await self.session.delete(sl_obj)

                res_th = await self.session.execute(
                    select(MotifStoryClaimThemeModel).where(MotifStoryClaimThemeModel.claim_id == c_model.id)
                )
                for th_obj in res_th.scalars().all():
                    await self.session.delete(th_obj)

                await self.session.flush()

                for sl in c_item.source_links:
                    src_obj = source_model_map[sl.source_key]
                    cs_link = MotifStoryClaimSourceModel(
                        id=uuid.uuid4(),
                        claim_id=c_model.id,
                        source_id=src_obj.id,
                        locator=sl.locator,
                        source_note=sl.source_note
                    )
                    self.session.add(cs_link)

                for t_key in c_item.theme_keys:
                    ct_link = MotifStoryClaimThemeModel(
                        id=uuid.uuid4(),
                        claim_id=c_model.id,
                        theme_key=t_key
                    )
                    self.session.add(ct_link)

        await self.session.commit()

        return ImportResult(
            dry_run=False,
            sources_created=sources_created_count,
            motifs_created=motifs_created_count,
            claims_created=claims_created_count,
            claim_sources_created=claim_sources_created_count,
            claim_themes_created=claim_themes_created_count
        )

    async def _get_existing_sources(self) -> Dict[str, CuratedSourceModel]:
        res = await self.session.execute(select(CuratedSourceModel))
        return {s.source_key: s for s in res.scalars().all()}

    async def _get_existing_motifs(self) -> Dict[str, MotifModel]:
        res = await self.session.execute(select(MotifModel))
        return {m.motif_key: m for m in res.scalars().all()}

    async def _get_existing_claims(self) -> Dict[str, MotifStoryClaimModel]:
        res = await self.session.execute(select(MotifStoryClaimModel))
        return {c.claim_key: c for c in res.scalars().all()}
