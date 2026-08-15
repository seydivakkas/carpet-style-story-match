"""Database repository for Narrative Affinity Engine v1."""
import hashlib
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.carpet import CarpetModel
from app.db.models.carpet_story_association import (
    CarpetStoryAssociationModel,
    CarpetMotifAssociationModel,
    CarpetMotifAssociationSourceModel
)
from app.db.models.motif_knowledge import MotifStoryClaimModel, MotifStoryClaimSourceModel
from app.db.models.preference_assessment import UserNarrativeProfileModel
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityResultModel,
    NarrativeAffinityThemeResultModel
)


class NarrativeAffinityRepository:
    """Database repository for Narrative Affinity persistence & queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_narrative_profile(self, assessment_id: uuid.UUID) -> Optional[UserNarrativeProfileModel]:
        stmt = (
            select(UserNarrativeProfileModel)
            .options(selectinload(UserNarrativeProfileModel.themes))
            .where(UserNarrativeProfileModel.assessment_id == assessment_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_carpet(self, carpet_id: uuid.UUID) -> Optional[CarpetModel]:
        stmt = select(CarpetModel).where(CarpetModel.id == carpet_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_carpet_story_associations(self, carpet_id: uuid.UUID) -> List[CarpetStoryAssociationModel]:
        stmt = (
            select(CarpetStoryAssociationModel)
            .options(
                selectinload(CarpetStoryAssociationModel.motif_association).selectinload(CarpetMotifAssociationModel.motif),
                selectinload(CarpetStoryAssociationModel.motif_association).selectinload(CarpetMotifAssociationModel.presence_sources).selectinload(CarpetMotifAssociationSourceModel.source),
                selectinload(CarpetStoryAssociationModel.claim).selectinload(MotifStoryClaimModel.themes),
                selectinload(CarpetStoryAssociationModel.claim).selectinload(MotifStoryClaimModel.sources).selectinload(MotifStoryClaimSourceModel.source)
            )
            .join(CarpetStoryAssociationModel.motif_association)
            .where(CarpetMotifAssociationModel.carpet_id == carpet_id)
            .order_by(CarpetStoryAssociationModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    def compute_snapshot_hash(story_associations: List[CarpetStoryAssociationModel]) -> str:
        items = []
        for sa in story_associations:
            claim = sa.claim
            claim_key = claim.claim_key if claim else ""
            claim_status = claim.status.value if claim else ""
            theme_keys = sorted([t.theme_key for t in claim.themes]) if claim and claim.themes else []
            app_note = sa.applicability_note or ""
            assoc_id = str(sa.carpet_motif_association_id)

            repr_str = f"assoc:{assoc_id}|claim:{claim_key}|status:{claim_status}|themes:{','.join(theme_keys)}|app_note:{app_note}"
            items.append(repr_str)

        items.sort()
        combined = "\n".join(items)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    async def get_affinity_result_by_snapshot(
        self,
        user_narrative_profile_id: uuid.UUID,
        carpet_id: uuid.UUID,
        snapshot_hash: str,
        affinity_version: str
    ) -> Optional[NarrativeAffinityResultModel]:
        stmt = (
            select(NarrativeAffinityResultModel)
            .options(
                selectinload(NarrativeAffinityResultModel.carpet),
                selectinload(NarrativeAffinityResultModel.theme_results)
            )
            .where(
                NarrativeAffinityResultModel.user_narrative_profile_id == user_narrative_profile_id,
                NarrativeAffinityResultModel.carpet_id == carpet_id,
                NarrativeAffinityResultModel.carpet_narrative_snapshot_hash == snapshot_hash,
                NarrativeAffinityResultModel.affinity_version == affinity_version
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_affinity_result(
        self,
        result_model: NarrativeAffinityResultModel,
        theme_models: List[NarrativeAffinityThemeResultModel]
    ) -> NarrativeAffinityResultModel:
        self.session.add(result_model)
        await self.session.flush()

        for tm in theme_models:
            tm.affinity_result_id = result_model.id
            self.session.add(tm)

        await self.session.commit()
        await self.session.refresh(result_model)

        # Reload with theme results
        stmt = (
            select(NarrativeAffinityResultModel)
            .options(
                selectinload(NarrativeAffinityResultModel.carpet),
                selectinload(NarrativeAffinityResultModel.theme_results)
            )
            .where(NarrativeAffinityResultModel.id == result_model.id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def get_affinity_result_by_id(
        self,
        affinity_id: uuid.UUID,
        assessment_id: uuid.UUID
    ) -> Optional[NarrativeAffinityResultModel]:
        stmt = (
            select(NarrativeAffinityResultModel)
            .options(
                selectinload(NarrativeAffinityResultModel.carpet),
                selectinload(NarrativeAffinityResultModel.theme_results)
            )
            .where(
                NarrativeAffinityResultModel.id == affinity_id,
                NarrativeAffinityResultModel.assessment_id == assessment_id
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_affinity_results(self, assessment_id: uuid.UUID) -> List[NarrativeAffinityResultModel]:
        stmt = (
            select(NarrativeAffinityResultModel)
            .options(
                selectinload(NarrativeAffinityResultModel.carpet),
                selectinload(NarrativeAffinityResultModel.theme_results)
            )
            .where(NarrativeAffinityResultModel.assessment_id == assessment_id)
            .order_by(NarrativeAffinityResultModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
