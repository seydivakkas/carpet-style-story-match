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
    AssessmentStatus,
    TextChoiceEnum
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
                selectinload(PreferenceAssessmentModel.profile).selectinload(TextPreferenceProfileModel.dimensions)
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
        # Check if response for question_key exists
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
        # Check if profile already exists
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
