"""Service for User Narrative Profile v1."""
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.preference_assessment import UserProfileStatusEnum, UserNarrativeProfileModel
from app.domain.preferences.exceptions import AssessmentNotFoundError
from app.domain.narrative.builder import NarrativeProfileBuilder, BuiltNarrativeProfile
from app.domain.narrative.exceptions import (
    NarrativeProfileRequiresReviewedPreferenceProfileError,
    NarrativeProfileNotFoundError,
    NarrativeProfileAlreadyExistsError,
)
from app.domain.narrative.repository import NarrativeProfileRepository
from app.domain.narrative.schemas import UserNarrativeProfileResponse


class NarrativeProfileService:
    """Service layer for user narrative profile orchestration."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = NarrativeProfileRepository(session)

    async def create_narrative_profile(
        self,
        assessment_id: uuid.UUID,
        skip: bool,
        primary_themes: List[str],
        secondary_themes: List[str]
    ) -> UserNarrativeProfileResponse:
        assessment = await self.repository.get_assessment_with_profiles(assessment_id)
        if not assessment:
            raise AssessmentNotFoundError(f"Assessment not found: {assessment_id}")

        if (
            not assessment.user_preference_profile
            or assessment.user_preference_profile.status != UserProfileStatusEnum.REVIEWED
        ):
            raise NarrativeProfileRequiresReviewedPreferenceProfileError(
                "Narrative Profile creation requires a reviewed UserPreferenceProfile"
            )

        # Build candidate profile
        built = NarrativeProfileBuilder.build(
            skip=skip,
            primary_themes=primary_themes,
            secondary_themes=secondary_themes
        )

        # Check existing profile idempotency / conflict
        existing_profile = await self.repository.get_narrative_profile_by_assessment(assessment_id)
        if existing_profile:
            if self._is_identical_profile(existing_profile, built):
                return UserNarrativeProfileResponse.model_validate(existing_profile)
            raise NarrativeProfileAlreadyExistsError(
                f"Narrative profile already exists for assessment {assessment_id} with different selections"
            )

        new_profile = await self.repository.create_narrative_profile(
            assessment_id=assessment_id,
            user_preference_profile_id=assessment.user_preference_profile.id,
            built_profile=built
        )
        await self.session.commit()

        return UserNarrativeProfileResponse.model_validate(new_profile)

    async def get_narrative_profile(
        self,
        assessment_id: uuid.UUID
    ) -> UserNarrativeProfileResponse:
        assessment = await self.repository.get_assessment_with_profiles(assessment_id)
        if not assessment:
            raise AssessmentNotFoundError(f"Assessment not found: {assessment_id}")

        profile = await self.repository.get_narrative_profile_by_assessment(assessment_id)
        if not profile:
            raise NarrativeProfileNotFoundError(
                f"Narrative Profile not found for assessment: {assessment_id}"
            )

        return UserNarrativeProfileResponse.model_validate(profile)

    def _is_identical_profile(
        self,
        existing: UserNarrativeProfileModel,
        candidate: BuiltNarrativeProfile
    ) -> bool:
        if existing.completion_mode != candidate.completion_mode:
            return False

        existing_theme_map = {t.theme_key: t.interest_level for t in existing.themes}
        for candidate_item in candidate.themes:
            if existing_theme_map.get(candidate_item.theme_key) != candidate_item.interest_level:
                return False

        return True
