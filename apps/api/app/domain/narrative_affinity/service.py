"""Service layer for Narrative Affinity Engine v1."""
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetSourceType
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityResultModel,
    NarrativeAffinityThemeResultModel
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.narrative_affinity.constants import NARRATIVE_AFFINITY_VERSION
from app.domain.narrative_affinity.engine import NarrativeAffinityEngine, EngineAffinityOutput, EngineThemeSnapshot
from app.domain.narrative_affinity.exceptions import (
    NarrativeProfileNotFoundError,
    NarrativeAffinityCarpetNotFoundError,
    NarrativeAffinityRequiresCatalogCarpetError,
    NarrativeAffinityNotFoundError
)
from app.domain.narrative_affinity.explanation import NarrativeAffinityExplanationBuilder
from app.domain.narrative_affinity.projector import CarpetNarrativeEvidenceProjector
from app.domain.narrative_affinity.repository import NarrativeAffinityRepository
from app.domain.narrative_affinity.schemas import (
    NarrativeAffinityResultRead,
    NarrativeAffinityDetailRead,
    NarrativeAffinityThemeResultRead
)


class NarrativeAffinityService:
    """Service layer for Narrative Affinity calculation and retrieval."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NarrativeAffinityRepository(session)

    async def calculate_narrative_affinity(
        self,
        assessment_id: uuid.UUID,
        carpet_id: uuid.UUID
    ) -> NarrativeAffinityDetailRead:
        user_profile = await self.repo.get_user_narrative_profile(assessment_id)
        if not user_profile:
            raise NarrativeProfileNotFoundError(f"User narrative profile not found for assessment: {assessment_id}")

        carpet = await self.repo.get_carpet(carpet_id)
        if not carpet:
            raise NarrativeAffinityCarpetNotFoundError(f"Carpet not found: {carpet_id}")

        if carpet.source_type != CarpetSourceType.CATALOG:
            raise NarrativeAffinityRequiresCatalogCarpetError(
                f"Narrative affinity requires catalog carpet (got {carpet.source_type})"
            )

        story_associations = await self.repo.list_carpet_story_associations(carpet_id)
        snapshot_hash = self.repo.compute_snapshot_hash(story_associations)

        # Check existing result for idempotency
        existing = await self.repo.get_affinity_result_by_snapshot(
            user_narrative_profile_id=user_profile.id,
            carpet_id=carpet_id,
            snapshot_hash=snapshot_hash,
            affinity_version=NARRATIVE_AFFINITY_VERSION
        )
        if existing:
            return await self._build_detail_read(existing, story_associations, user_profile)

        # Execute pure engine
        engine_output = NarrativeAffinityEngine.calculate_affinity(
            user_narrative_profile=user_profile,
            carpet_source_type=carpet.source_type,
            story_associations=story_associations
        )

        result_model = NarrativeAffinityResultModel(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_narrative_profile_id=user_profile.id,
            carpet_id=carpet_id,
            affinity_version=engine_output.affinity_version,
            carpet_narrative_snapshot_hash=snapshot_hash,
            status=engine_output.status,
            not_available_reason=engine_output.not_available_reason,
            affinity_level=engine_output.affinity_level,
            confirmed_interest_coverage=engine_output.confirmed_interest_coverage,
            selected_theme_count=engine_output.selected_theme_count,
            selected_interest_weight=engine_output.selected_interest_weight,
            confirmed_matched_theme_count=engine_output.confirmed_matched_theme_count,
            confirmed_matched_interest_weight=engine_output.confirmed_matched_interest_weight,
            contested_overlap_count=engine_output.contested_overlap_count
        )

        theme_models: List[NarrativeAffinityThemeResultModel] = []
        for snapshot in engine_output.theme_snapshots:
            tm = NarrativeAffinityThemeResultModel(
                id=uuid.uuid4(),
                theme_key=snapshot.theme_key,
                user_interest_level=snapshot.user_interest_level,
                user_interest_weight=snapshot.user_interest_weight,
                user_selected=snapshot.user_selected,
                carpet_support_status=snapshot.carpet_support_status,
                confirmed_match=snapshot.confirmed_match,
                contested_overlap=snapshot.contested_overlap,
                has_contested_evidence=snapshot.has_contested_evidence,
                evidence=snapshot.evidence
            )
            theme_models.append(tm)

        saved_result = await self.repo.create_affinity_result(result_model, theme_models)
        return await self._build_detail_read(saved_result, story_associations, user_profile)

    async def get_narrative_affinity_detail(
        self,
        assessment_id: uuid.UUID,
        affinity_id: uuid.UUID
    ) -> NarrativeAffinityDetailRead:
        result = await self.repo.get_affinity_result_by_id(affinity_id, assessment_id)
        if not result:
            raise NarrativeAffinityNotFoundError(f"Narrative affinity result not found: {affinity_id}")

        user_profile = await self.repo.get_user_narrative_profile(assessment_id)
        story_associations = await self.repo.list_carpet_story_associations(result.carpet_id)

        return await self._build_detail_read(result, story_associations, user_profile)

    async def list_narrative_affinities(self, assessment_id: uuid.UUID) -> List[NarrativeAffinityResultRead]:
        results = await self.repo.list_affinity_results(assessment_id)
        out: List[NarrativeAffinityResultRead] = []
        for r in results:
            out.append(self._to_result_read(r))
        return out

    async def _build_detail_read(
        self,
        result_model: NarrativeAffinityResultModel,
        story_associations: List[CarpetStoryAssociationModel],
        user_profile: Optional[UserNarrativeProfileModel]
    ) -> NarrativeAffinityDetailRead:
        # Re-run engine output for explanation generation
        carpet_source_type = result_model.carpet.source_type if result_model.carpet else CarpetSourceType.CATALOG

        if user_profile:
            engine_output = NarrativeAffinityEngine.calculate_affinity(
                user_narrative_profile=user_profile,
                carpet_source_type=carpet_source_type,
                story_associations=story_associations
            )
        else:
            # Fallback output construction from snapshot rows
            engine_output = self._reconstruct_engine_output(result_model, story_associations)

        explanation = NarrativeAffinityExplanationBuilder.build_explanation(engine_output)
        result_read = self._to_result_read(result_model)

        return NarrativeAffinityDetailRead(
            result=result_read,
            explanation=explanation
        )

    @classmethod
    def _to_result_read(cls, result_model: NarrativeAffinityResultModel) -> NarrativeAffinityResultRead:
        # Sort theme results canonically
        canonical_map = {t["key"]: i for i, t in enumerate(CANONICAL_NARRATIVE_THEMES)}
        sorted_themes = sorted(
            result_model.theme_results,
            key=lambda tr: canonical_map.get(tr.theme_key, 999)
        )

        theme_reads = [
            NarrativeAffinityThemeResultRead.model_validate(tr)
            for tr in sorted_themes
        ]

        return NarrativeAffinityResultRead(
            id=result_model.id,
            assessment_id=result_model.assessment_id,
            user_narrative_profile_id=result_model.user_narrative_profile_id,
            carpet_id=result_model.carpet_id,
            affinity_version=result_model.affinity_version,
            carpet_narrative_snapshot_hash=result_model.carpet_narrative_snapshot_hash,
            status=result_model.status,
            not_available_reason=result_model.not_available_reason,
            affinity_level=result_model.affinity_level,
            confirmed_interest_coverage=result_model.confirmed_interest_coverage,
            selected_theme_count=result_model.selected_theme_count,
            selected_interest_weight=result_model.selected_interest_weight,
            confirmed_matched_theme_count=result_model.confirmed_matched_theme_count,
            confirmed_matched_interest_weight=result_model.confirmed_matched_interest_weight,
            contested_overlap_count=result_model.contested_overlap_count,
            created_at=result_model.created_at,
            theme_results=theme_reads
        )

    @staticmethod
    def _reconstruct_engine_output(
        result_model: NarrativeAffinityResultModel,
        story_associations: List[CarpetStoryAssociationModel]
    ) -> EngineAffinityOutput:
        evidence_projections = CarpetNarrativeEvidenceProjector.project_evidence(story_associations)
        canonical_map = {t["key"]: i for i, t in enumerate(CANONICAL_NARRATIVE_THEMES)}

        sorted_tr = sorted(
            result_model.theme_results,
            key=lambda tr: canonical_map.get(tr.theme_key, 999)
        )

        snapshots: List[EngineThemeSnapshot] = []
        for tr in sorted_tr:
            proj = evidence_projections.get(tr.theme_key)
            story_assocs = proj.story_associations if proj else []

            snapshots.append(
                EngineThemeSnapshot(
                    theme_key=tr.theme_key,
                    user_interest_level=tr.user_interest_level,
                    user_interest_weight=tr.user_interest_weight,
                    user_selected=tr.user_selected,
                    carpet_support_status=tr.carpet_support_status,
                    confirmed_match=tr.confirmed_match,
                    contested_overlap=tr.contested_overlap,
                    has_contested_evidence=tr.has_contested_evidence,
                    evidence=tr.evidence,
                    story_associations=story_assocs
                )
            )

        return EngineAffinityOutput(
            affinity_version=result_model.affinity_version,
            status=result_model.status,
            not_available_reason=result_model.not_available_reason,
            affinity_level=result_model.affinity_level,
            confirmed_interest_coverage=result_model.confirmed_interest_coverage,
            selected_theme_count=result_model.selected_theme_count,
            selected_interest_weight=result_model.selected_interest_weight,
            confirmed_matched_theme_count=result_model.confirmed_matched_theme_count,
            confirmed_matched_interest_weight=result_model.confirmed_matched_interest_weight,
            contested_overlap_count=result_model.contested_overlap_count,
            theme_snapshots=snapshots
        )
