"""CarpetCatalogImporter for Carpet Catalog + Curated Story Associations v1."""
from dataclasses import dataclass
from typing import Dict, Set, Optional, Tuple, List
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.domain.carpet_catalog.constants import (
    CARPET_CATALOG_SCHEMA_VERSION,
)
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
    UnsupportedSchemaVersionError,
)
from app.domain.carpet_catalog.schemas import CatalogImportDataset


@dataclass(frozen=True)
class CatalogImportResult:
    dry_run: bool
    carpets_created: int
    motif_associations_created: int
    presence_sources_created: int
    story_associations_created: int


class CarpetCatalogImporter:
    """Importer for catalog carpets and curated motif/story associations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_dataset(
        self,
        dataset: CatalogImportDataset,
        dry_run: bool = False
    ) -> CatalogImportResult:
        # 1. Schema version check
        if dataset.schema_version != CARPET_CATALOG_SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Unsupported schema_version: {dataset.schema_version}. Expected: {CARPET_CATALOG_SCHEMA_VERSION}"
            )

        # 2. Check SKU validity and input duplicates
        input_skus: List[str] = []
        for c in dataset.carpets:
            trimmed_sku = c.sku.strip() if c.sku else ""
            if not trimmed_sku:
                raise CatalogSkuRequiredError("Catalog carpet input missing valid non-empty SKU")
            input_skus.append(trimmed_sku)

        if len(input_skus) != len(set(input_skus)):
            raise CatalogConflictError("Duplicate SKU found within input dataset")

        # 3. Fetch existing DB records
        existing_carpets = await self._get_existing_carpets()
        existing_motifs = await self._get_existing_motifs()
        existing_sources = await self._get_existing_sources()
        existing_claims = await self._get_existing_claims()

        # 4. Check SKU conflicts
        for c_input in dataset.carpets:
            sku = c_input.sku.strip()
            if sku in existing_carpets:
                ex_carpet = existing_carpets[sku]
                if ex_carpet.source_type != CarpetSourceType.CATALOG:
                    raise CatalogSkuConflictError(
                        f"SKU '{sku}' conflicts with an existing non-catalog carpet (source_type={ex_carpet.source_type})"
                    )
                # Check material metadata conflicts
                if ex_carpet.name != c_input.name:
                    raise CatalogConflictError(
                        f"Catalog SKU '{sku}' metadata conflicts with existing carpet record name"
                    )

        # 5. Validate association rules for all carpets in input
        for c_input in dataset.carpets:
            motif_keys_in_carpet = [m.motif_key for m in c_input.motifs]
            if len(motif_keys_in_carpet) != len(set(motif_keys_in_carpet)):
                raise CurationConflictError(
                    f"Carpet SKU '{c_input.sku}' contains duplicate motif_key in motifs array"
                )

            for m_input in c_input.motifs:
                if m_input.motif_key not in existing_motifs:
                    raise CatalogUnknownMotifError(
                        f"Carpet SKU '{c_input.sku}' references unknown motif_key: '{m_input.motif_key}'"
                    )
                motif_obj = existing_motifs[m_input.motif_key]

                # Evidence type invariants
                ev = m_input.evidence_type
                if ev == MotifEvidenceTypeEnum.CURATOR_CONFIRMED:
                    if not m_input.curation_note or not m_input.curation_note.strip():
                        raise CarpetMotifCurationNoteRequiredError(
                            f"CURATOR_CONFIRMED motif '{m_input.motif_key}' on SKU '{c_input.sku}' requires curation_note"
                        )

                elif ev == MotifEvidenceTypeEnum.SOURCE_DOCUMENTED:
                    if len(m_input.sources) < 1:
                        raise CarpetMotifSourceRequiredError(
                            f"SOURCE_DOCUMENTED motif '{m_input.motif_key}' on SKU '{c_input.sku}' requires at least 1 source link"
                        )

                elif ev == MotifEvidenceTypeEnum.UNCERTAIN:
                    if not m_input.uncertainty_note or not m_input.uncertainty_note.strip():
                        raise CarpetMotifUncertaintyNoteRequiredError(
                            f"UNCERTAIN motif '{m_input.motif_key}' on SKU '{c_input.sku}' requires uncertainty_note"
                        )
                    if len(m_input.story_claim_keys) > 0:
                        raise CarpetUncertainMotifCannotHaveStoryError(
                            f"UNCERTAIN motif '{m_input.motif_key}' on SKU '{c_input.sku}' cannot carry story claim associations"
                        )

                # Check presence sources
                source_keys_in_motif = [s.source_key for s in m_input.sources]
                if len(source_keys_in_motif) != len(set(source_keys_in_motif)):
                    raise CurationConflictError(
                        f"Motif '{m_input.motif_key}' on SKU '{c_input.sku}' has duplicate source_key in presence sources"
                    )

                for s_link in m_input.sources:
                    if s_link.source_key not in existing_sources:
                        raise CatalogUnknownSourceError(
                            f"Motif '{m_input.motif_key}' on SKU '{c_input.sku}' references unknown source_key: '{s_link.source_key}'"
                        )

                # Check story claim keys
                claim_keys_in_motif = [sc.claim_key for sc in m_input.story_claim_keys]
                if len(claim_keys_in_motif) != len(set(claim_keys_in_motif)):
                    raise CurationConflictError(
                        f"Motif '{m_input.motif_key}' on SKU '{c_input.sku}' has duplicate claim_key in story_claim_keys"
                    )

                for sc_link in m_input.story_claim_keys:
                    if sc_link.claim_key not in existing_claims:
                        raise CatalogUnknownClaimError(
                            f"Motif '{m_input.motif_key}' on SKU '{c_input.sku}' references unknown claim_key: '{sc_link.claim_key}'"
                        )
                    claim_obj = existing_claims[sc_link.claim_key]

                    # Motif mismatch check
                    if claim_obj.motif_id != motif_obj.id:
                        raise CarpetStoryMotifMismatchError(
                            f"Claim '{sc_link.claim_key}' belongs to motif '{claim_obj.motif_id}', but associated with motif '{motif_obj.id}' on SKU '{c_input.sku}'"
                        )

                    # UNKNOWN claim check
                    if claim_obj.status == MotifStoryStatusEnum.UNKNOWN:
                        raise CarpetStoryUnknownClaimNotApplicableError(
                            f"UNKNOWN status claim '{sc_link.claim_key}' cannot be attached as positive story to SKU '{c_input.sku}'"
                        )

                    # CONTEXTUAL or CONTESTED claim applicability note check
                    if claim_obj.status in (MotifStoryStatusEnum.CONTEXTUAL, MotifStoryStatusEnum.CONTESTED):
                        if not sc_link.applicability_note or not sc_link.applicability_note.strip():
                            raise CarpetStoryApplicabilityNoteRequiredError(
                                f"{claim_obj.status} claim '{sc_link.claim_key}' on SKU '{c_input.sku}' requires applicability_note"
                            )

        if dry_run:
            carpets_to_create = sum(1 for c in dataset.carpets if c.sku.strip() not in existing_carpets)
            motif_assocs_to_create = sum(len(c.motifs) for c in dataset.carpets)
            sources_to_create = sum(sum(len(m.sources) for m in c.motifs) for c in dataset.carpets)
            stories_to_create = sum(sum(len(m.story_claim_keys) for m in c.motifs) for c in dataset.carpets)

            return CatalogImportResult(
                dry_run=True,
                carpets_created=carpets_to_create,
                motif_associations_created=motif_assocs_to_create,
                presence_sources_created=sources_to_create,
                story_associations_created=stories_to_create
            )

        # 6. Atomic Execution Phase
        carpets_created_count = 0
        motif_assocs_created_count = 0
        presence_sources_created_count = 0
        stories_created_count = 0

        for c_input in dataset.carpets:
            sku = c_input.sku.strip()

            if sku in existing_carpets:
                carpet_obj = existing_carpets[sku]
            else:
                carpet_obj = CarpetModel(
                    id=uuid.uuid4(),
                    sku=sku,
                    name=c_input.name,
                    description=c_input.description,
                    manufacturer=c_input.manufacturer,
                    collection=c_input.collection,
                    width_cm=c_input.width_cm,
                    height_cm=c_input.height_cm,
                    material=c_input.material,
                    style_label=c_input.style_label,
                    source_type=CarpetSourceType.CATALOG,
                    source_reference=c_input.source_reference,
                    is_active=c_input.is_active
                )
                self.session.add(carpet_obj)
                existing_carpets[sku] = carpet_obj
                carpets_created_count += 1

            await self.session.flush()

            # Create motif associations
            for m_input in c_input.motifs:
                motif_obj = existing_motifs[m_input.motif_key]

                # Check if association already exists for (carpet_id, motif_id)
                existing_assoc = await self._get_existing_motif_association(carpet_obj.id, motif_obj.id)
                if existing_assoc:
                    # Conflict check if materially different
                    if existing_assoc.evidence_type != m_input.evidence_type:
                        raise CurationConflictError(
                            f"Motif association conflict for SKU '{sku}' and motif '{m_input.motif_key}': evidence_type mismatch"
                        )
                    assoc_obj = existing_assoc
                else:
                    assoc_obj = CarpetMotifAssociationModel(
                        id=uuid.uuid4(),
                        carpet_id=carpet_obj.id,
                        motif_id=motif_obj.id,
                        evidence_type=m_input.evidence_type,
                        curation_note=m_input.curation_note,
                        uncertainty_note=m_input.uncertainty_note
                    )
                    self.session.add(assoc_obj)
                    motif_assocs_created_count += 1
                    await self.session.flush()

                # Create presence source links
                existing_presence_src_ids = await self._get_existing_presence_source_ids(assoc_obj.id)
                for s_link in m_input.sources:
                    src_obj = existing_sources[s_link.source_key]
                    if src_obj.id not in existing_presence_src_ids:
                        assoc_src = CarpetMotifAssociationSourceModel(
                            id=uuid.uuid4(),
                            association_id=assoc_obj.id,
                            source_id=src_obj.id,
                            locator=s_link.locator,
                            source_note=s_link.source_note
                        )
                        self.session.add(assoc_src)
                        existing_presence_src_ids.add(src_obj.id)
                        presence_sources_created_count += 1

                # Create story associations
                existing_claim_ids = await self._get_existing_story_claim_ids(assoc_obj.id)
                for sc_link in m_input.story_claim_keys:
                    claim_obj = existing_claims[sc_link.claim_key]
                    if claim_obj.id not in existing_claim_ids:
                        story_assoc = CarpetStoryAssociationModel(
                            id=uuid.uuid4(),
                            carpet_motif_association_id=assoc_obj.id,
                            claim_id=claim_obj.id,
                            applicability_note=sc_link.applicability_note
                        )
                        self.session.add(story_assoc)
                        existing_claim_ids.add(claim_obj.id)
                        stories_created_count += 1

        await self.session.commit()

        return CatalogImportResult(
            dry_run=False,
            carpets_created=carpets_created_count,
            motif_associations_created=motif_assocs_created_count,
            presence_sources_created=presence_sources_created_count,
            story_associations_created=stories_created_count
        )

    async def _get_existing_carpets(self) -> Dict[str, CarpetModel]:
        res = await self.session.execute(select(CarpetModel).where(CarpetModel.sku.isnot(None)))
        return {c.sku: c for c in res.scalars().all() if c.sku}

    async def _get_existing_motifs(self) -> Dict[str, MotifModel]:
        res = await self.session.execute(select(MotifModel))
        return {m.motif_key: m for m in res.scalars().all()}

    async def _get_existing_sources(self) -> Dict[str, CuratedSourceModel]:
        res = await self.session.execute(select(CuratedSourceModel))
        return {s.source_key: s for s in res.scalars().all()}

    async def _get_existing_claims(self) -> Dict[str, MotifStoryClaimModel]:
        res = await self.session.execute(select(MotifStoryClaimModel))
        return {c.claim_key: c for c in res.scalars().all()}

    async def _get_existing_motif_association(
        self,
        carpet_id: uuid.UUID,
        motif_id: uuid.UUID
    ) -> Optional[CarpetMotifAssociationModel]:
        stmt = select(CarpetMotifAssociationModel).where(
            CarpetMotifAssociationModel.carpet_id == carpet_id,
            CarpetMotifAssociationModel.motif_id == motif_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def _get_existing_presence_source_ids(self, assoc_id: uuid.UUID) -> Set[uuid.UUID]:
        stmt = select(CarpetMotifAssociationSourceModel.source_id).where(
            CarpetMotifAssociationSourceModel.association_id == assoc_id
        )
        res = await self.session.execute(stmt)
        return set(res.scalars().all())

    async def _get_existing_story_claim_ids(self, assoc_id: uuid.UUID) -> Set[uuid.UUID]:
        stmt = select(CarpetStoryAssociationModel.claim_id).where(
            CarpetStoryAssociationModel.carpet_motif_association_id == assoc_id
        )
        res = await self.session.execute(stmt)
        return set(res.scalars().all())
