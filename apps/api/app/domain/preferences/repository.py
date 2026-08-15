import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    TextPreferenceResponseModel,
    TextPreferenceProfileModel,
    TextPreferenceDimensionModel,
    VisualPreferencePresentationModel,
    VisualPreferenceResponseModel,
    VisualPreferenceProfileModel,
    VisualPreferenceDimensionModel,
    UserPreferenceProfileModel,
    UserPreferenceDimensionModel,
    PreferenceConfidenceProfileModel,
    PreferenceConfidenceDimensionModel,
    ImportanceProfileModel,
    ImportanceDimensionModel,
    AssessmentStatus,
    TextChoiceEnum,
    VisualChoiceEnum,
    UserProfileStatusEnum,
    UserPreferenceProvenanceEnum,
    ConfidenceStatusEnum,
    ImportanceLevelEnum,
    ImportanceCompletionModeEnum
)

class PreferenceAssessmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_assessment(
        self,
        evidence_version: str = "text-preference-evidence-v1"
    ) -> PreferenceAssessmentModel:
        assessment = PreferenceAssessmentModel(
            status=AssessmentStatus.TEXT_PENDING,
            evidence_version=evidence_version
        )
        self.session.add(assessment)
        await self.session.commit()
        await self.session.refresh(assessment)
        return assessment

    async def get_assessment_by_id(self, assessment_id: uuid.UUID) -> Optional[PreferenceAssessmentModel]:
        stmt = (
            select(PreferenceAssessmentModel)
            .options(
                selectinload(PreferenceAssessmentModel.responses),
                selectinload(PreferenceAssessmentModel.profile).selectinload(TextPreferenceProfileModel.dimensions),
                selectinload(PreferenceAssessmentModel.visual_presentations),
                selectinload(PreferenceAssessmentModel.visual_responses),
                selectinload(PreferenceAssessmentModel.visual_profile).selectinload(VisualPreferenceProfileModel.dimensions),
                selectinload(PreferenceAssessmentModel.user_preference_profile).selectinload(UserPreferenceProfileModel.dimensions),
                selectinload(PreferenceAssessmentModel.confidence_profile).selectinload(PreferenceConfidenceProfileModel.dimensions),
                selectinload(PreferenceAssessmentModel.importance_profile).selectinload(ImportanceProfileModel.dimensions),
            )
            .where(PreferenceAssessmentModel.id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_text_response(
        self,
        assessment_id: uuid.UUID,
        question_key: str,
        choice: TextChoiceEnum,
        response_value: float
    ) -> TextPreferenceResponseModel:
        stmt = select(TextPreferenceResponseModel).where(
            TextPreferenceResponseModel.assessment_id == assessment_id,
            TextPreferenceResponseModel.question_key == question_key
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.choice = choice
            existing.response_value = response_value
            resp_model = existing
        else:
            resp_model = TextPreferenceResponseModel(
                assessment_id=assessment_id,
                question_key=question_key,
                choice=choice,
                response_value=response_value
            )
            self.session.add(resp_model)

        await self.session.commit()
        await self.session.refresh(resp_model)
        return resp_model

    async def get_responses_by_assessment_id(self, assessment_id: uuid.UUID) -> List[TextPreferenceResponseModel]:
        stmt = (
            select(TextPreferenceResponseModel)
            .where(TextPreferenceResponseModel.assessment_id == assessment_id)
            .order_by(TextPreferenceResponseModel.question_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_text_profile(
        self,
        assessment_id: uuid.UUID,
        evidence_version: str,
        dimensions: List[Dict[str, Any]]
    ) -> TextPreferenceProfileModel:
        stmt = select(TextPreferenceProfileModel).where(TextPreferenceProfileModel.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            return existing_profile

        profile = TextPreferenceProfileModel(
            assessment_id=assessment_id,
            evidence_version=evidence_version
        )
        self.session.add(profile)
        await self.session.flush()

        for d in dimensions:
            dim = TextPreferenceDimensionModel(
                profile_id=profile.id,
                dimension_key=d["dimension_key"],
                value=d["value"],
                status=d["status"],
                evidence_weight=d["evidence_weight"],
                evidence_count=d["evidence_count"]
            )
            self.session.add(dim)

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile

    async def get_text_profile_by_assessment_id(self, assessment_id: uuid.UUID) -> Optional[TextPreferenceProfileModel]:
        stmt = (
            select(TextPreferenceProfileModel)
            .options(selectinload(TextPreferenceProfileModel.dimensions))
            .where(TextPreferenceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_assessment_status(
        self,
        assessment_id: uuid.UUID,
        status: AssessmentStatus
    ) -> PreferenceAssessmentModel:
        assessment = await self.get_assessment_by_id(assessment_id)
        if assessment:
            assessment.status = status
            await self.session.commit()
            await self.session.refresh(assessment)
        return assessment

    # ---------------------------------------------------------
    # VISUAL PREFERENCE REPOSITORY METHODS (GÖREV 05)
    # ---------------------------------------------------------

    async def bulk_create_visual_presentations(
        self,
        assessment_id: uuid.UUID,
        presentations_data: List[Dict[str, Any]]
    ) -> List[VisualPreferencePresentationModel]:
        existing_stmt = select(VisualPreferencePresentationModel).where(
            VisualPreferencePresentationModel.assessment_id == assessment_id
        )
        result = await self.session.execute(existing_stmt)
        existing_list = list(result.scalars().all())

        if existing_list and len(existing_list) == len(presentations_data):
            return existing_list

        created_list = []
        for p in presentations_data:
            pres = VisualPreferencePresentationModel(
                assessment_id=assessment_id,
                stimulus_key=p["stimulus_key"],
                stimulus_version=p["stimulus_version"],
                left_variant=p["left_variant"],
                right_variant=p["right_variant"],
                left_asset_sha256=p["left_asset_sha256"],
                right_asset_sha256=p["right_asset_sha256"]
            )
            self.session.add(pres)
            created_list.append(pres)

        await self.session.commit()
        for pres in created_list:
            await self.session.refresh(pres)
        return created_list

    async def get_visual_presentations_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> List[VisualPreferencePresentationModel]:
        stmt = (
            select(VisualPreferencePresentationModel)
            .where(VisualPreferencePresentationModel.assessment_id == assessment_id)
            .order_by(VisualPreferencePresentationModel.stimulus_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_visual_presentation_by_key(
        self,
        assessment_id: uuid.UUID,
        stimulus_key: str
    ) -> Optional[VisualPreferencePresentationModel]:
        stmt = select(VisualPreferencePresentationModel).where(
            VisualPreferencePresentationModel.assessment_id == assessment_id,
            VisualPreferencePresentationModel.stimulus_key == stimulus_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_visual_response(
        self,
        assessment_id: uuid.UUID,
        stimulus_key: str,
        choice: VisualChoiceEnum,
        canonical_direction: float
    ) -> VisualPreferenceResponseModel:
        stmt = select(VisualPreferenceResponseModel).where(
            VisualPreferenceResponseModel.assessment_id == assessment_id,
            VisualPreferenceResponseModel.stimulus_key == stimulus_key
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.choice = choice
            existing.canonical_direction = canonical_direction
            resp_model = existing
        else:
            resp_model = VisualPreferenceResponseModel(
                assessment_id=assessment_id,
                stimulus_key=stimulus_key,
                choice=choice,
                canonical_direction=canonical_direction
            )
            self.session.add(resp_model)

        await self.session.commit()
        await self.session.refresh(resp_model)
        return resp_model

    async def get_visual_responses_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> List[VisualPreferenceResponseModel]:
        stmt = (
            select(VisualPreferenceResponseModel)
            .where(VisualPreferenceResponseModel.assessment_id == assessment_id)
            .order_by(VisualPreferenceResponseModel.stimulus_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_visual_profile(
        self,
        assessment_id: uuid.UUID,
        evidence_version: str,
        stimulus_version: str,
        dimensions: List[Dict[str, Any]]
    ) -> VisualPreferenceProfileModel:
        stmt = select(VisualPreferenceProfileModel).where(VisualPreferenceProfileModel.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            return existing_profile

        profile = VisualPreferenceProfileModel(
            assessment_id=assessment_id,
            evidence_version=evidence_version,
            stimulus_version=stimulus_version
        )
        self.session.add(profile)
        await self.session.flush()

        for d in dimensions:
            dim = VisualPreferenceDimensionModel(
                profile_id=profile.id,
                dimension_key=d["dimension_key"],
                value=d["value"],
                status=d["status"],
                evidence_weight=d["evidence_weight"],
                evidence_count=d["evidence_count"]
            )
            self.session.add(dim)

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile

    async def get_visual_profile_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[VisualPreferenceProfileModel]:
        stmt = (
            select(VisualPreferenceProfileModel)
            .options(selectinload(VisualPreferenceProfileModel.dimensions))
            .where(VisualPreferenceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ---------------------------------------------------------
    # MULTIMODAL PREFERENCE REPOSITORY METHODS (GÖREV 06)
    # ---------------------------------------------------------

    async def create_user_preference_profile(
        self,
        assessment_id: uuid.UUID,
        profile_version: str,
        dimensions: List[Dict[str, Any]]
    ) -> UserPreferenceProfileModel:
        stmt = select(UserPreferenceProfileModel).where(
            UserPreferenceProfileModel.assessment_id == assessment_id,
            UserPreferenceProfileModel.profile_version == profile_version
        ).options(selectinload(UserPreferenceProfileModel.dimensions))
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        profile = UserPreferenceProfileModel(
            assessment_id=assessment_id,
            profile_version=profile_version,
            status=UserProfileStatusEnum.DRAFT
        )
        self.session.add(profile)
        await self.session.flush()

        for d in dimensions:
            dim = UserPreferenceDimensionModel(
                profile_id=profile.id,
                dimension_key=d["dimension_key"],
                inferred_value=d["inferred_value"],
                final_value=d["final_value"],
                status=d["status"],
                provenance=d.get("provenance", UserPreferenceProvenanceEnum.INFERRED),
                text_value=d.get("text_value"),
                text_evidence_weight=d.get("text_evidence_weight", 0.0),
                visual_value=d.get("visual_value"),
                visual_evidence_weight=d.get("visual_evidence_weight", 0.0)
            )
            self.session.add(dim)

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile

    async def create_confidence_profile(
        self,
        assessment_id: uuid.UUID,
        preference_profile_id: uuid.UUID,
        confidence_version: str,
        dimensions: List[Dict[str, Any]]
    ) -> PreferenceConfidenceProfileModel:
        stmt = select(PreferenceConfidenceProfileModel).where(
            PreferenceConfidenceProfileModel.preference_profile_id == preference_profile_id,
            PreferenceConfidenceProfileModel.confidence_version == confidence_version
        ).options(selectinload(PreferenceConfidenceProfileModel.dimensions))
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        conf_profile = PreferenceConfidenceProfileModel(
            assessment_id=assessment_id,
            preference_profile_id=preference_profile_id,
            confidence_version=confidence_version
        )
        self.session.add(conf_profile)
        await self.session.flush()

        for d in dimensions:
            dim = PreferenceConfidenceDimensionModel(
                confidence_profile_id=conf_profile.id,
                dimension_key=d["dimension_key"],
                confidence=d["confidence"],
                status=d["status"],
                modality_count=d["modality_count"],
                agreement=d["agreement"],
                source_coverage=d["source_coverage"],
                evidence_json=d.get("evidence_json")
            )
            self.session.add(dim)

        await self.session.commit()
        await self.session.refresh(conf_profile, attribute_names=["dimensions"])
        return conf_profile

    async def get_user_preference_profile_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[UserPreferenceProfileModel]:
        stmt = (
            select(UserPreferenceProfileModel)
            .options(selectinload(UserPreferenceProfileModel.dimensions))
            .where(UserPreferenceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_confidence_profile_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[PreferenceConfidenceProfileModel]:
        stmt = (
            select(PreferenceConfidenceProfileModel)
            .options(selectinload(PreferenceConfidenceProfileModel.dimensions))
            .where(PreferenceConfidenceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def override_user_preference_dimension(
        self,
        profile_id: uuid.UUID,
        dimension_key: str,
        new_value: float
    ) -> UserPreferenceDimensionModel:
        stmt = select(UserPreferenceDimensionModel).where(
            UserPreferenceDimensionModel.profile_id == profile_id,
            UserPreferenceDimensionModel.dimension_key == dimension_key
        )
        result = await self.session.execute(stmt)
        dim = result.scalar_one_or_none()
        if not dim:
            from app.domain.preferences.exceptions import PreferenceDimensionNotFoundError
            raise PreferenceDimensionNotFoundError(dimension_key)

        dim.final_value = new_value
        dim.provenance = UserPreferenceProvenanceEnum.USER_OVERRIDDEN
        await self.session.commit()
        await self.session.refresh(dim)
        return dim

    async def confirm_user_preference_profile(
        self,
        assessment_id: uuid.UUID
    ) -> UserPreferenceProfileModel:
        stmt = (
            select(UserPreferenceProfileModel)
            .options(selectinload(UserPreferenceProfileModel.dimensions))
            .where(UserPreferenceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            from app.domain.preferences.exceptions import PreferenceProfileNotFoundError
            raise PreferenceProfileNotFoundError(assessment_id)

        # Update dimensions provenance
        for dim in profile.dimensions:
            if dim.provenance == UserPreferenceProvenanceEnum.INFERRED:
                dim.provenance = UserPreferenceProvenanceEnum.USER_CONFIRMED

        profile.status = UserProfileStatusEnum.REVIEWED

        # Update assessment status
        assessment_stmt = select(PreferenceAssessmentModel).where(PreferenceAssessmentModel.id == assessment_id)
        ass_result = await self.session.execute(assessment_stmt)
        assessment = ass_result.scalar_one_or_none()
        if assessment:
            assessment.status = AssessmentStatus.PROFILE_REVIEWED

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile

    async def get_importance_profile_by_assessment_id(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[ImportanceProfileModel]:
        stmt = (
            select(ImportanceProfileModel)
            .options(selectinload(ImportanceProfileModel.dimensions))
            .where(ImportanceProfileModel.assessment_id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_importance_profile(
        self,
        assessment_id: uuid.UUID,
        user_preference_profile_id: uuid.UUID,
        completion_mode: ImportanceCompletionModeEnum,
        dimensions_data: List[Dict[str, Any]],
        importance_version: str = "importance-v1"
    ) -> ImportanceProfileModel:
        profile = ImportanceProfileModel(
            assessment_id=assessment_id,
            user_preference_profile_id=user_preference_profile_id,
            importance_version=importance_version,
            completion_mode=completion_mode
        )
        self.session.add(profile)
        await self.session.flush()

        for dim in dimensions_data:
            dim_model = ImportanceDimensionModel(
                importance_profile_id=profile.id,
                dimension_key=dim["dimension_key"],
                level=dim["level"],
                weight=dim["weight"]
            )
            self.session.add(dim_model)

        # Update assessment status to IMPORTANCE_COMPLETE
        assessment_stmt = select(PreferenceAssessmentModel).where(PreferenceAssessmentModel.id == assessment_id)
        ass_result = await self.session.execute(assessment_stmt)
        assessment = ass_result.scalar_one_or_none()
        if assessment:
            assessment.status = AssessmentStatus.IMPORTANCE_COMPLETE

        await self.session.commit()
        await self.session.refresh(profile, attribute_names=["dimensions"])
        return profile
