"""Pure deterministic NarrativeProfileBuilder for User Narrative Profile v1."""
from dataclasses import dataclass
from typing import Dict, List
from app.db.models.preference_assessment import NarrativeInterestLevelEnum, NarrativeCompletionModeEnum
from app.domain.narrative.constants import (
    CANONICAL_NARRATIVE_THEMES,
    INTEREST_LEVEL_WEIGHTS,
    MAX_PRIMARY_THEMES,
    MAX_SECONDARY_THEMES,
)
from app.domain.narrative.exceptions import (
    NarrativeSelectionEmptyError,
    NarrativeSelectionOverlapError,
    NarrativeSelectionDuplicateError,
    NarrativeSelectionTooManyPrimaryError,
    NarrativeSelectionTooManySecondaryError,
    NarrativeSelectionUnknownThemeError,
    NarrativeSkipConflictError,
)


@dataclass(frozen=True)
class BuiltThemeItem:
    theme_key: str
    interest_level: NarrativeInterestLevelEnum
    interest_weight: float


@dataclass(frozen=True)
class BuiltNarrativeProfile:
    completion_mode: NarrativeCompletionModeEnum
    themes: List[BuiltThemeItem]


class NarrativeProfileBuilder:
    """Pure deterministic builder for creating canonical 8-theme user narrative profiles."""

    @staticmethod
    def build(
        skip: bool,
        primary_themes: List[str],
        secondary_themes: List[str]
    ) -> BuiltNarrativeProfile:
        if skip:
            if primary_themes or secondary_themes:
                raise NarrativeSkipConflictError(
                    "Cannot specify primary or secondary themes when skip=true"
                )
            completion_mode = NarrativeCompletionModeEnum.SKIPPED
            theme_items = [
                BuiltThemeItem(
                    theme_key=key,
                    interest_level=NarrativeInterestLevelEnum.NOT_SELECTED,
                    interest_weight=INTEREST_LEVEL_WEIGHTS["NOT_SELECTED"]
                )
                for key in CANONICAL_NARRATIVE_THEMES
            ]
            return BuiltNarrativeProfile(
                completion_mode=completion_mode,
                themes=theme_items
            )

        # Check explicit empty selection
        if not primary_themes and not secondary_themes:
            raise NarrativeSelectionEmptyError(
                "Must select at least one theme in primary or secondary when skip=false"
            )

        # Check duplicates within lists
        if len(primary_themes) != len(set(primary_themes)):
            raise NarrativeSelectionDuplicateError(
                "Duplicate theme keys found in primary_themes"
            )
        if len(secondary_themes) != len(set(secondary_themes)):
            raise NarrativeSelectionDuplicateError(
                "Duplicate theme keys found in secondary_themes"
            )

        # Check unknown themes
        canonical_set = set(CANONICAL_NARRATIVE_THEMES)
        for theme in primary_themes:
            if theme not in canonical_set:
                raise NarrativeSelectionUnknownThemeError(
                    f"Unknown primary narrative theme: {theme}"
                )
        for theme in secondary_themes:
            if theme not in canonical_set:
                raise NarrativeSelectionUnknownThemeError(
                    f"Unknown secondary narrative theme: {theme}"
                )

        # Check overlap
        overlap = set(primary_themes).intersection(set(secondary_themes))
        if overlap:
            raise NarrativeSelectionOverlapError(
                f"Themes cannot be in both primary and secondary: {sorted(list(overlap))}"
            )

        # Check max lengths
        if len(primary_themes) > MAX_PRIMARY_THEMES:
            raise NarrativeSelectionTooManyPrimaryError(
                f"Maximum of {MAX_PRIMARY_THEMES} primary themes allowed, got {len(primary_themes)}"
            )
        if len(secondary_themes) > MAX_SECONDARY_THEMES:
            raise NarrativeSelectionTooManySecondaryError(
                f"Maximum of {MAX_SECONDARY_THEMES} secondary themes allowed, got {len(secondary_themes)}"
            )

        primary_set = set(primary_themes)
        secondary_set = set(secondary_themes)
        completion_mode = NarrativeCompletionModeEnum.EXPLICIT_SELECTION

        theme_items: List[BuiltThemeItem] = []
        for key in CANONICAL_NARRATIVE_THEMES:
            if key in primary_set:
                level = NarrativeInterestLevelEnum.PRIMARY
            elif key in secondary_set:
                level = NarrativeInterestLevelEnum.SECONDARY
            else:
                level = NarrativeInterestLevelEnum.NOT_SELECTED

            weight = INTEREST_LEVEL_WEIGHTS[level.value]
            theme_items.append(
                BuiltThemeItem(
                    theme_key=key,
                    interest_level=level,
                    interest_weight=weight
                )
            )

        return BuiltNarrativeProfile(
            completion_mode=completion_mode,
            themes=theme_items
        )
