"""Repository for User Narrative Profile v1."""
from typing import Optional, List
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    UserNarrativeProfileModel,
    UserNarrativeThemeModel,
)
from app.domain.narrative.builder import BuiltNarrativeProfile
from app.domain.narrative.constants import (
    USER_NARRATIVE_PROFILE_VERSION,
    CANONICAL_NARRATIVE_THEMES,
)


class NarrativeProfileRepository:
    """Database repository for user narrative profiles."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_assessment_with_profiles(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[PreferenceAssessmentModel]:
        stmt = (
            select(PreferenceAssessmentModel)
            .options(
                selectinload(PreferenceAssessmentModel.user_preference_profile),
                selectinload(PreferenceAssessmentModel.narrative_profile).selectinload(UserNarrativeProfileModel.themes),
            )
            .where(PreferenceAssessmentModel.id == assessment_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_narrative_profile_by_assessment(
        self,
        assessment_id: uuid.UUID
    ) -> Optional[UserNarrativeProfileModel]:
        stmt = (
            select(UserNarrativeProfileModel)
            .options(selectinload(UserNarrativeProfileModel.themes))
            .where(
                UserNarrativeProfileModel.assessment_id == assessment_id,
                UserNarrativeProfileModel.profile_version == USER_NARRATIVE_PROFILE_VERSION
            )
        )
        res = await self.session.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile and profile.themes:
            # Enforce canonical N1->N8 order
            canonical_map = {t.theme_key: t for t in profile.themes}
            ordered_themes: List[UserNarrativeThemeModel] = []
            for key in CANONICAL_NARRATIVE_THEMES:
                if key in canonical_map:
                    ordered_themes.append(canonical_map[key])
            profile.themes = ordered_themes
        return profile

    async def create_narrative_profile(
        self,
        assessment_id: uuid.UUID,
        user_preference_profile_id: uuid.UUID,
        built_profile: BuiltNarrativeProfile
    ) -> UserNarrativeProfileModel:
        profile_model = UserNarrativeProfileModel(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_preference_profile_id=user_preference_profile_id,
            profile_version=USER_NARRATIVE_PROFILE_VERSION,
            completion_mode=built_profile.completion_mode
        )

        themes: List[UserNarrativeThemeModel] = []
        for item in built_profile.themes:
            themes.append(
                UserNarrativeThemeModel(
                    id=uuid.uuid4(),
                    narrative_profile_id=profile_model.id,
                    theme_key=item.theme_key,
                    interest_level=item.interest_level,
                    interest_weight=item.interest_weight
                )
            )

        profile_model.themes = themes
        self.session.add(profile_model)
        await self.session.flush()

        # Enforce canonical N1->N8 order
        canonical_map = {t.theme_key: t for t in themes}
        profile_model.themes = [canonical_map[key] for key in CANONICAL_NARRATIVE_THEMES if key in canonical_map]

        return profile_model
