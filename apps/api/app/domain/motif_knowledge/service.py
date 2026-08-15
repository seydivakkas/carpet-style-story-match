"""Service layer for Motif Story Knowledge read queries."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.motif_knowledge import MotifStoryStatusEnum, MotifModel, MotifStoryClaimModel, CuratedSourceModel
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.motif_knowledge.exceptions import (
    MotifNotFoundError,
    ClaimNotFoundError,
    SourceNotFoundError,
)
from app.domain.motif_knowledge.repository import MotifKnowledgeRepository
from app.domain.motif_knowledge.schemas import (
    MotifRead,
    MotifListResponse,
    MotifStoryClaimRead,
    MotifStoryClaimListResponse,
    MotifStoryClaimSummaryRead,
    CuratedSourceRead,
    ClaimSourceRead,
)


class MotifKnowledgeService:
    """Service layer for read-only motif knowledge operations."""

    def __init__(self, session: AsyncSession):
        self.repo = MotifKnowledgeRepository(session)

    async def list_motifs(
        self,
        limit: int = 20,
        offset: int = 0,
        story_status: Optional[MotifStoryStatusEnum] = None,
        narrative_theme: Optional[str] = None
    ) -> MotifListResponse:
        motifs, total_count = await self.repo.list_motifs(
            limit=limit,
            offset=offset,
            story_status=story_status,
            narrative_theme=narrative_theme
        )
        return MotifListResponse(
            total_count=total_count,
            motifs=[self._to_motif_read(m) for m in motifs]
        )

    async def get_motif(self, identifier: str) -> MotifRead:
        motif = await self.repo.get_motif_by_id_or_key(identifier)
        if not motif:
            raise MotifNotFoundError(f"Motif not found: {identifier}")
        return self._to_motif_read(motif)

    async def list_claims(
        self,
        limit: int = 20,
        offset: int = 0,
        motif_id_or_key: Optional[str] = None,
        status: Optional[MotifStoryStatusEnum] = None,
        narrative_theme: Optional[str] = None
    ) -> MotifStoryClaimListResponse:
        claims, total_count = await self.repo.list_claims(
            limit=limit,
            offset=offset,
            motif_id_or_key=motif_id_or_key,
            status=status,
            narrative_theme=narrative_theme
        )
        return MotifStoryClaimListResponse(
            total_count=total_count,
            claims=[self._to_claim_read(c) for c in claims]
        )

    async def get_claim(self, identifier: str) -> MotifStoryClaimRead:
        claim = await self.repo.get_claim_by_id_or_key(identifier)
        if not claim:
            raise ClaimNotFoundError(f"Motif story claim not found: {identifier}")
        return self._to_claim_read(claim)

    async def get_source(self, identifier: str) -> CuratedSourceRead:
        source = await self.repo.get_source_by_id_or_key(identifier)
        if not source:
            raise SourceNotFoundError(f"Curated source not found: {identifier}")
        return CuratedSourceRead.model_validate(source)

    def _to_motif_read(self, motif: MotifModel) -> MotifRead:
        claims_summary: List[MotifStoryClaimSummaryRead] = []
        if motif.story_claims:
            # Order claims deterministically by claim_key ASC
            sorted_claims = sorted(motif.story_claims, key=lambda c: c.claim_key)
            for c in sorted_claims:
                themes_ordered = self._order_themes([t.theme_key for t in c.themes])
                claims_summary.append(
                    MotifStoryClaimSummaryRead(
                        id=c.id,
                        claim_key=c.claim_key,
                        status=c.status,
                        claim_text_tr=c.claim_text_tr,
                        claim_text_en=c.claim_text_en,
                        context_note=c.context_note,
                        contest_note=c.contest_note,
                        uncertainty_note=c.uncertainty_note,
                        themes=themes_ordered
                    )
                )

        return MotifRead(
            id=motif.id,
            motif_key=motif.motif_key,
            name_tr=motif.name_tr,
            name_en=motif.name_en,
            visual_description_tr=motif.visual_description_tr,
            visual_description_en=motif.visual_description_en,
            created_at=motif.created_at,
            updated_at=motif.updated_at,
            story_claims=claims_summary
        )

    def _to_claim_read(self, claim: MotifStoryClaimModel) -> MotifStoryClaimRead:
        themes_ordered = self._order_themes([t.theme_key for t in claim.themes])

        sources_read: List[ClaimSourceRead] = []
        if claim.sources:
            # Order sources deterministically by source_key ASC
            sorted_sources = sorted(claim.sources, key=lambda cs: cs.source.source_key)
            for cs in sorted_sources:
                sources_read.append(
                    ClaimSourceRead(
                        source=CuratedSourceRead.model_validate(cs.source),
                        locator=cs.locator,
                        source_note=cs.source_note
                    )
                )

        return MotifStoryClaimRead(
            id=claim.id,
            claim_key=claim.claim_key,
            motif_id=claim.motif_id,
            motif_key=claim.motif.motif_key if claim.motif else "",
            status=claim.status,
            claim_text_tr=claim.claim_text_tr,
            claim_text_en=claim.claim_text_en,
            context_note=claim.context_note,
            contest_note=claim.contest_note,
            uncertainty_note=claim.uncertainty_note,
            knowledge_version=claim.knowledge_version,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            themes=themes_ordered,
            sources=sources_read
        )

    @staticmethod
    def _order_themes(theme_keys: List[str]) -> List[str]:
        """Order theme keys according to canonical Narrative Themes N1..N8 order."""
        canonical_map = {t["key"]: i for i, t in enumerate(CANONICAL_NARRATIVE_THEMES)}
        return sorted(theme_keys, key=lambda k: canonical_map.get(k, 999))
