import uuid
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    TextPreferenceResponseModel,
    TextPreferenceProfileModel,
    AssessmentStatus,
    TextChoiceEnum
)
from app.domain.preferences.constants import (
    TEXT_PREFERENCE_EVIDENCE_VERSION,
    CANONICAL_TEXT_QUESTIONS,
    TEXT_CHOICE_MAP
)
from app.domain.preferences.aggregator import TextPreferenceAggregator
from app.domain.preferences.repository import PreferenceAssessmentRepository
from app.domain.preferences.exceptions import (
    AssessmentNotFoundError,
    TextPreferencesIncompleteError,
    TextPreferencesAlreadyCompletedError,
    InvalidQuestionKeyError
)

VALID_QUESTION_KEYS = {q["question_key"] for q in CANONICAL_TEXT_QUESTIONS}
CANONICAL_ORDER_MAP = {q["question_key"]: q["order"] for q in CANONICAL_TEXT_QUESTIONS}

class PreferenceAssessmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PreferenceAssessmentRepository(session)

    async def create_assessment(self) -> PreferenceAssessmentModel:
        return await self.repo.create_assessment(evidence_version=TEXT_PREFERENCE_EVIDENCE_VERSION)

    async def get_assessment(self, assessment_id: uuid.UUID) -> PreferenceAssessmentModel:
        assessment = await self.repo.get_assessment_by_id(assessment_id)
        if not assessment:
            raise AssessmentNotFoundError(assessment_id)
        return assessment

    async def save_text_response(
        self,
        assessment_id: uuid.UUID,
        question_key: str,
        choice: TextChoiceEnum
    ) -> TextPreferenceResponseModel:
        if question_key not in VALID_QUESTION_KEYS:
            raise InvalidQuestionKeyError(question_key)

        assessment = await self.get_assessment(assessment_id)
        if assessment.status == AssessmentStatus.TEXT_COMPLETE:
            raise TextPreferencesAlreadyCompletedError(assessment_id)

        response_value = TEXT_CHOICE_MAP[choice]
        return await self.repo.upsert_text_response(
            assessment_id=assessment_id,
            question_key=question_key,
            choice=choice,
            response_value=response_value
        )

    async def get_text_responses(self, assessment_id: uuid.UUID) -> List[TextPreferenceResponseModel]:
        await self.get_assessment(assessment_id)
        responses = await self.repo.get_responses_by_assessment_id(assessment_id)
        # Order by canonical T1 -> T6 order
        responses.sort(key=lambda r: CANONICAL_ORDER_MAP.get(r.question_key, 99))
        return responses

    async def complete_text_assessment(self, assessment_id: uuid.UUID) -> TextPreferenceProfileModel:
        assessment = await self.get_assessment(assessment_id)

        # Check if already completed (Idempotency)
        existing_profile = await self.repo.get_text_profile_by_assessment_id(assessment_id)
        if assessment.status == AssessmentStatus.TEXT_COMPLETE and existing_profile:
            return existing_profile

        # Fetch current text responses
        responses = await self.repo.get_responses_by_assessment_id(assessment_id)
        answered_keys = {r.question_key for r in responses}
        missing_keys = [q for q in VALID_QUESTION_KEYS if q not in answered_keys]

        if len(answered_keys) < len(VALID_QUESTION_KEYS):
            missing_keys.sort(key=lambda k: CANONICAL_ORDER_MAP.get(k, 99))
            raise TextPreferencesIncompleteError(
                assessment_id=assessment_id,
                answered_count=len(answered_keys),
                missing_keys=missing_keys
            )

        # Map to responses dict
        responses_dict = {r.question_key: r.response_value for r in responses}

        # Run matrix aggregation
        dimensions_data = TextPreferenceAggregator.aggregate(responses_dict)

        # Create profile
        profile = await self.repo.create_text_profile(
            assessment_id=assessment_id,
            evidence_version=TEXT_PREFERENCE_EVIDENCE_VERSION,
            dimensions=dimensions_data
        )

        # Lock assessment as TEXT_COMPLETE
        await self.repo.update_assessment_status(assessment_id, status=AssessmentStatus.TEXT_COMPLETE)

        return profile

    async def get_text_profile(self, assessment_id: uuid.UUID) -> TextPreferenceProfileModel:
        await self.get_assessment(assessment_id)
        profile = await self.repo.get_text_profile_by_assessment_id(assessment_id)
        if not profile:
            responses = await self.repo.get_responses_by_assessment_id(assessment_id)
            answered_keys = {r.question_key for r in responses}
            missing_keys = sorted(list(VALID_QUESTION_KEYS - answered_keys), key=lambda k: CANONICAL_ORDER_MAP.get(k, 99))
            raise TextPreferencesIncompleteError(
                assessment_id=assessment_id,
                answered_count=len(answered_keys),
                missing_keys=missing_keys
            )
        return profile
