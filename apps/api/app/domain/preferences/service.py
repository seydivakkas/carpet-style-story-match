import uuid
import random
import os
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    TextPreferenceResponseModel,
    TextPreferenceProfileModel,
    VisualPreferencePresentationModel,
    VisualPreferenceResponseModel,
    VisualPreferenceProfileModel,
    AssessmentStatus,
    TextChoiceEnum,
    VisualChoiceEnum
)
from app.domain.preferences.constants import (
    TEXT_PREFERENCE_EVIDENCE_VERSION,
    VISUAL_PREFERENCE_STIMULI_VERSION,
    VISUAL_PREFERENCE_EVIDENCE_VERSION,
    CANONICAL_TEXT_QUESTIONS,
    TEXT_CHOICE_MAP,
    VISUAL_CHOICE_DISPLAY_SCALE
)
from app.domain.preferences.aggregator import (
    TextPreferenceAggregator,
    VisualPreferenceAggregator
)
from app.domain.preferences.visual_stimuli import (
    CANONICAL_VISUAL_CARDS,
    generate_and_save_all_stimuli
)
from app.domain.preferences.repository import PreferenceAssessmentRepository
from app.domain.preferences.exceptions import (
    AssessmentNotFoundError,
    TextPreferencesIncompleteError,
    TextPreferencesAlreadyCompletedError,
    InvalidQuestionKeyError,
    VisualPhaseRequiresTextCompleteError,
    VisualPreferencesIncompleteError,
    VisualPreferencesAlreadyCompletedError,
    InvalidStimulusKeyError,
    VisualProfileNotFoundError
)

VALID_QUESTION_KEYS = {q["question_key"] for q in CANONICAL_TEXT_QUESTIONS}
CANONICAL_ORDER_MAP = {q["question_key"]: idx for idx, q in enumerate(CANONICAL_TEXT_QUESTIONS)}

VALID_STIMULUS_KEYS = set(CANONICAL_VISUAL_CARDS)
VISUAL_CANONICAL_ORDER_MAP = {key: idx for idx, key in enumerate(CANONICAL_VISUAL_CARDS)}

# Target directory for generated visual stimulus assets
STIMULI_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "stimuli", VISUAL_PREFERENCE_STIMULI_VERSION)

class PreferenceAssessmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PreferenceAssessmentRepository(session)
        # Ensure stimuli assets generated on service init
        self.asset_hashes = generate_and_save_all_stimuli(STIMULI_ASSETS_DIR)

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
        if assessment.status in (AssessmentStatus.TEXT_COMPLETE, AssessmentStatus.VISUAL_PENDING, AssessmentStatus.VISUAL_COMPLETE):
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
        responses.sort(key=lambda r: CANONICAL_ORDER_MAP.get(r.question_key, 99))
        return responses

    async def complete_text_assessment(self, assessment_id: uuid.UUID) -> TextPreferenceProfileModel:
        assessment = await self.get_assessment(assessment_id)

        existing_profile = await self.repo.get_text_profile_by_assessment_id(assessment_id)
        if assessment.status in (AssessmentStatus.TEXT_COMPLETE, AssessmentStatus.VISUAL_PENDING, AssessmentStatus.VISUAL_COMPLETE) and existing_profile:
            return existing_profile

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

        responses_dict = {r.question_key: r.response_value for r in responses}
        dimensions_data = TextPreferenceAggregator.aggregate(responses_dict)

        profile = await self.repo.create_text_profile(
            assessment_id=assessment_id,
            evidence_version=TEXT_PREFERENCE_EVIDENCE_VERSION,
            dimensions=dimensions_data
        )

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

    # ---------------------------------------------------------
    # VISUAL PREFERENCE SERVICE METHODS (GÖREV 05)
    # ---------------------------------------------------------

    async def start_visual_phase(
        self,
        assessment_id: uuid.UUID
    ) -> List[VisualPreferencePresentationModel]:
        assessment = await self.get_assessment(assessment_id)

        # Precondition check: requires TEXT_COMPLETE status
        if assessment.status == AssessmentStatus.TEXT_PENDING:
            raise VisualPhaseRequiresTextCompleteError(assessment_id, assessment.status.value)

        # Check existing presentations (Idempotent)
        existing_presentations = await self.repo.get_visual_presentations_by_assessment_id(assessment_id)
        if existing_presentations and len(existing_presentations) == len(CANONICAL_VISUAL_CARDS):
            return existing_presentations

        # Generate side permutations (LEFT/RIGHT randomization)
        presentations_data = []
        # Fixed seed based on assessment UUID to ensure reproducible presentation side per assessment
        rng = random.Random(str(assessment_id))

        for card_key in CANONICAL_VISUAL_CARDS:
            left_v, right_v = rng.choice([("A", "B"), ("B", "A")])
            left_hash = self.asset_hashes.get(f"{card_key}_{left_v}", "")
            right_hash = self.asset_hashes.get(f"{card_key}_{right_v}", "")

            presentations_data.append({
                "stimulus_key": card_key,
                "stimulus_version": VISUAL_PREFERENCE_STIMULI_VERSION,
                "left_variant": left_v,
                "right_variant": right_v,
                "left_asset_sha256": left_hash,
                "right_asset_sha256": right_hash
            })

        created = await self.repo.bulk_create_visual_presentations(assessment_id, presentations_data)

        if assessment.status != AssessmentStatus.VISUAL_COMPLETE:
            await self.repo.update_assessment_status(assessment_id, status=AssessmentStatus.VISUAL_PENDING)

        return created

    async def get_visual_presentations(
        self,
        assessment_id: uuid.UUID
    ) -> List[VisualPreferencePresentationModel]:
        await self.get_assessment(assessment_id)
        presentations = await self.repo.get_visual_presentations_by_assessment_id(assessment_id)
        presentations.sort(key=lambda p: VISUAL_CANONICAL_ORDER_MAP.get(p.stimulus_key, 99))
        return presentations

    async def save_visual_response(
        self,
        assessment_id: uuid.UUID,
        stimulus_key: str,
        choice: VisualChoiceEnum
    ) -> VisualPreferenceResponseModel:
        if stimulus_key not in VALID_STIMULUS_KEYS:
            raise InvalidStimulusKeyError(stimulus_key)

        assessment = await self.get_assessment(assessment_id)
        if assessment.status == AssessmentStatus.VISUAL_COMPLETE:
            raise VisualPreferencesAlreadyCompletedError(assessment_id)

        # Lookup presentation to resolve side polarity
        presentation = await self.repo.get_visual_presentation_by_key(assessment_id, stimulus_key)
        if not presentation:
            # Auto-start visual phase if presentation missing
            presentations = await self.start_visual_phase(assessment_id)
            presentation = next((p for p in presentations if p.stimulus_key == stimulus_key), None)

        display_val = VISUAL_CHOICE_DISPLAY_SCALE[choice]

        # Server-side polarity resolution
        # If LEFT is variant A (low pole): display_val maps directly (-1 -> A, +1 -> B)
        # If LEFT is variant B (high pole): display_val inverts (-1 -> B (+1.0), +1 -> A (-1.0))
        if presentation.left_variant == "A":
            canonical_direction = display_val
        else:
            canonical_direction = -display_val

        return await self.repo.upsert_visual_response(
            assessment_id=assessment_id,
            stimulus_key=stimulus_key,
            choice=choice,
            canonical_direction=canonical_direction
        )

    async def get_visual_responses(
        self,
        assessment_id: uuid.UUID
    ) -> List[VisualPreferenceResponseModel]:
        await self.get_assessment(assessment_id)
        responses = await self.repo.get_visual_responses_by_assessment_id(assessment_id)
        responses.sort(key=lambda r: VISUAL_CANONICAL_ORDER_MAP.get(r.stimulus_key, 99))
        return responses

    async def complete_visual_assessment(
        self,
        assessment_id: uuid.UUID
    ) -> VisualPreferenceProfileModel:
        assessment = await self.get_assessment(assessment_id)

        existing_profile = await self.repo.get_visual_profile_by_assessment_id(assessment_id)
        if assessment.status == AssessmentStatus.VISUAL_COMPLETE and existing_profile:
            return existing_profile

        responses = await self.repo.get_visual_responses_by_assessment_id(assessment_id)
        answered_keys = {r.stimulus_key for r in responses}
        missing_keys = [s for s in CANONICAL_VISUAL_CARDS if s not in answered_keys]

        if len(answered_keys) < len(CANONICAL_VISUAL_CARDS):
            missing_keys.sort(key=lambda k: VISUAL_CANONICAL_ORDER_MAP.get(k, 99))
            raise VisualPreferencesIncompleteError(
                assessment_id=assessment_id,
                answered_count=len(answered_keys),
                missing_keys=missing_keys
            )

        canonical_directions = {r.stimulus_key: r.canonical_direction for r in responses}
        dimensions_data = VisualPreferenceAggregator.aggregate(canonical_directions)

        profile = await self.repo.create_visual_profile(
            assessment_id=assessment_id,
            evidence_version=VISUAL_PREFERENCE_EVIDENCE_VERSION,
            stimulus_version=VISUAL_PREFERENCE_STIMULI_VERSION,
            dimensions=dimensions_data
        )

        await self.repo.update_assessment_status(assessment_id, status=AssessmentStatus.VISUAL_COMPLETE)
        return profile

    async def get_visual_profile(
        self,
        assessment_id: uuid.UUID
    ) -> VisualPreferenceProfileModel:
        await self.get_assessment(assessment_id)
        profile = await self.repo.get_visual_profile_by_assessment_id(assessment_id)
        if not profile:
            raise VisualProfileNotFoundError(assessment_id)
        return profile
