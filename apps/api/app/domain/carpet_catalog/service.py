"""Service layer for Carpet Catalog & Story Association read operations."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.carpet_catalog.exceptions import CatalogCarpetNotFoundError
from app.domain.carpet_catalog.repository import CarpetCatalogRepository
from app.domain.images.storage import get_image_storage
from app.domain.carpet_catalog.schemas import (
    CatalogCarpetRead,
    CatalogCarpetListResponse,
    CatalogCarpetDetailRead,
    CarpetMotifAssociationRead,
    CarpetStoryAssociationRead,
    PrimaryImageSummary,
    StyleDnaReadinessEnum,
    BrandRead,
    BrandListResponse,
)
from app.domain.common.readiness import derive_style_dna_readiness
from app.domain.motif_knowledge.schemas import CuratedSourceRead, ClaimSourceRead


class CarpetCatalogService:
    """Service layer for side-effect-free catalog queries."""

    def __init__(self, session: AsyncSession):
        self.repo = CarpetCatalogRepository(session)
        self.storage = get_image_storage()

    async def list_brands(self, verified_only: bool = False) -> BrandListResponse:
        brands, total_count = await self.repo.list_brands(verified_only=verified_only)
        brand_reads = [BrandRead.model_validate(b) for b in brands]
        return BrandListResponse(total_count=total_count, brands=brand_reads)

    async def get_brand_detail(self, brand_key: str) -> BrandRead:
        brand = await self.repo.get_brand_by_key(brand_key)
        if not brand:
            raise CatalogCarpetNotFoundError(f"Manufacturer brand not found: {brand_key}")
        return BrandRead.model_validate(brand)

    async def list_catalog_carpets(
        self,
        limit: int = 20,
        offset: int = 0,
        manufacturer: Optional[str] = None,
        brand_key: Optional[str] = None,
        collection: Optional[str] = None,
        material: Optional[str] = None,
        style_label: Optional[str] = None
    ) -> CatalogCarpetListResponse:
        carpets, total_count = await self.repo.list_catalog_carpets(
            limit=limit,
            offset=offset,
            manufacturer=manufacturer,
            brand_key=brand_key,
            collection=collection,
            material=material,
            style_label=style_label
        )
        carpet_reads = []
        for c in carpets:
            primary_img = await self.repo.get_primary_image(c.id)
            current_profile = await self.repo.get_current_style_profile(c.id)
            readiness = derive_style_dna_readiness(primary_img, current_profile)

            primary_img_summary = None
            if primary_img:
                is_avail = self.storage.image_exists(primary_img.storage_key)
                primary_img_summary = PrimaryImageSummary(
                    image_id=primary_img.id,
                    file_path=primary_img.storage_key,
                    width=primary_img.width_px,
                    height=primary_img.height_px,
                    image_available=is_avail
                )

            c_read = CatalogCarpetRead.model_validate(c)
            if c.brand:
                c_read.brand = BrandRead.model_validate(c.brand)
            c_read.primary_image = primary_img_summary
            c_read.style_dna_readiness = readiness
            carpet_reads.append(c_read)

        return CatalogCarpetListResponse(
            total_count=total_count,
            carpets=carpet_reads
        )

    async def get_catalog_carpet_detail(self, identifier: str) -> CatalogCarpetDetailRead:
        carpet = await self.repo.get_catalog_carpet_by_id_or_sku(identifier)
        if not carpet:
            raise CatalogCarpetNotFoundError(f"Catalog carpet not found: {identifier}")

        primary_image = await self.repo.get_primary_image(carpet.id)
        current_profile = await self.repo.get_current_style_profile(carpet.id)

        # Derive Style DNA readiness state side-effect-free
        readiness = derive_style_dna_readiness(primary_image, current_profile)

        primary_img_summary = None
        if primary_image:
            is_avail = self.storage.image_exists(primary_image.storage_key)
            primary_img_summary = PrimaryImageSummary(
                image_id=primary_image.id,
                file_path=primary_image.storage_key,
                width=primary_image.width_px,
                height=primary_image.height_px,
                image_available=is_avail
            )

        motif_assocs = await self.repo.list_carpet_motif_associations(carpet.id)
        story_assocs = await self.repo.list_carpet_story_associations(carpet.id)

        carpet_read = CatalogCarpetRead.model_validate(carpet)
        if carpet.brand:
            carpet_read.brand = BrandRead.model_validate(carpet.brand)

        return CatalogCarpetDetailRead(
            carpet=carpet_read,
            primary_image=primary_img_summary,
            style_dna_readiness=readiness,
            motif_association_count=len(motif_assocs),
            story_association_count=len(story_assocs)
        )

    async def list_carpet_motifs(self, identifier: str) -> List[CarpetMotifAssociationRead]:
        carpet = await self.repo.get_catalog_carpet_by_id_or_sku(identifier)
        if not carpet:
            raise CatalogCarpetNotFoundError(f"Catalog carpet not found: {identifier}")

        assocs = await self.repo.list_carpet_motif_associations(carpet.id)
        result: List[CarpetMotifAssociationRead] = []

        for a in assocs:
            presence_sources: List[ClaimSourceRead] = []
            if a.presence_sources:
                sorted_srcs = sorted(a.presence_sources, key=lambda ps: ps.source.source_key)
                for ps in sorted_srcs:
                    presence_sources.append(
                        ClaimSourceRead(
                            source=CuratedSourceRead.model_validate(ps.source),
                            locator=ps.locator,
                            source_note=ps.source_note
                        )
                    )

            result.append(
                CarpetMotifAssociationRead(
                    id=a.id,
                    carpet_id=a.carpet_id,
                    motif_id=a.motif_id,
                    motif_key=a.motif.motif_key,
                    motif_name_tr=a.motif.name_tr,
                    evidence_type=a.evidence_type,
                    curation_note=a.curation_note,
                    uncertainty_note=a.uncertainty_note,
                    presence_sources=presence_sources,
                    story_association_count=len(a.story_associations)
                )
            )

        return result

    async def list_carpet_story_associations(self, identifier: str) -> List[CarpetStoryAssociationRead]:
        carpet = await self.repo.get_catalog_carpet_by_id_or_sku(identifier)
        if not carpet:
            raise CatalogCarpetNotFoundError(f"Catalog carpet not found: {identifier}")

        story_assocs = await self.repo.list_carpet_story_associations(carpet.id)
        result: List[CarpetStoryAssociationRead] = []

        for sa in story_assocs:
            motif_assoc = sa.motif_association
            claim = sa.claim

            # 1. Presence sources from carpet_motif_association
            presence_srcs: List[ClaimSourceRead] = []
            if motif_assoc.presence_sources:
                sorted_ps = sorted(motif_assoc.presence_sources, key=lambda ps: ps.source.source_key)
                for ps in sorted_ps:
                    presence_srcs.append(
                        ClaimSourceRead(
                            source=CuratedSourceRead.model_validate(ps.source),
                            locator=ps.locator,
                            source_note=ps.source_note
                        )
                    )

            # 2. Claim sources from motif_story_claim
            claim_srcs: List[ClaimSourceRead] = []
            if claim.sources:
                sorted_cs = sorted(claim.sources, key=lambda cs: cs.source.source_key)
                for cs in sorted_cs:
                    claim_srcs.append(
                        ClaimSourceRead(
                            source=CuratedSourceRead.model_validate(cs.source),
                            locator=cs.locator,
                            source_note=cs.source_note
                        )
                    )

            # Themes in canonical N1..N8 order
            themes_ordered = self._order_themes([t.theme_key for t in claim.themes])

            result.append(
                CarpetStoryAssociationRead(
                    id=sa.id,
                    carpet_motif_association_id=sa.carpet_motif_association_id,
                    motif_key=motif_assoc.motif.motif_key,
                    motif_name_tr=motif_assoc.motif.name_tr,
                    motif_evidence_type=motif_assoc.evidence_type,
                    claim_id=claim.id,
                    claim_key=claim.claim_key,
                    status=claim.status,
                    claim_text_tr=claim.claim_text_tr,
                    context_note=claim.context_note,
                    contest_note=claim.contest_note,
                    applicability_note=sa.applicability_note,
                    themes=themes_ordered,
                    presence_sources=presence_srcs,
                    claim_sources=claim_srcs
                )
            )

        return result

    @staticmethod
    def _order_themes(theme_keys: List[str]) -> List[str]:
        canonical_map = {t["key"]: i for i, t in enumerate(CANONICAL_NARRATIVE_THEMES)}
        return sorted(theme_keys, key=lambda k: canonical_map.get(k, 999))
