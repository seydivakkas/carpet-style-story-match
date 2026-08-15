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
    AssessmentStatus,
    TextChoiceEnum,
    VisualChoiceEnum
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
