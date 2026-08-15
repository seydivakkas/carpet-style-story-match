from typing import List, Tuple, Dict, Any
from app.domain.contracts import CANONICAL_STYLE_DNA
from app.db.models.preference_assessment import (
    ImportanceLevelEnum,
    ImportanceCompletionModeEnum
)
from app.domain.preferences.constants import (
    MAX_PRIORITY_DIMENSIONS,
    MAX_FLEXIBLE_DIMENSIONS,
    IMPORTANCE_LEVEL_WEIGHTS
)
from app.domain.preferences.exceptions import (
    ImportanceSelectionTooManyPriorityError,
    ImportanceSelectionTooManyFlexibleError,
    ImportanceSelectionOverlapError,
    ImportanceSelectionDuplicateError,
    ImportanceSelectionUnknownDimensionError,
    ImportanceSelectionInvalidSkipError,
    ImportanceSelectionEmptyError
)

CANONICAL_KEYS = [d["key"] for d in CANONICAL_STYLE_DNA]

class ImportanceProfileBuilder:
    """
    Pure deterministic domain builder for Importance Profiles.
    Validates explicit user selection rules and produces canonical 9D level and weight records.
    Zero side effects, zero database dependency.
    """

    @classmethod
    def build(
        cls,
        skip: bool,
        priority_dimensions: List[str],
        flexible_dimensions: List[str]
    ) -> Tuple[ImportanceCompletionModeEnum, List[Dict[str, Any]]]:

        if skip:
            if priority_dimensions or flexible_dimensions:
                raise ImportanceSelectionInvalidSkipError()

            completion_mode = ImportanceCompletionModeEnum.SKIPPED_ALL_STANDARD
            results = []
            for key in CANONICAL_KEYS:
                results.append({
                    "dimension_key": key,
                    "level": ImportanceLevelEnum.STANDARD,
                    "weight": IMPORTANCE_LEVEL_WEIGHTS["STANDARD"]
                })
            return completion_mode, results

        # Explicit selection mode validation
        if not priority_dimensions and not flexible_dimensions:
            raise ImportanceSelectionEmptyError()

        # Check duplicates in input arrays
        seen_p = set()
        dup_p = [x for x in priority_dimensions if x in seen_p or seen_p.add(x)]
        seen_f = set()
        dup_f = [x for x in flexible_dimensions if x in seen_f or seen_f.add(x)]
        all_dups = list(set(dup_p + dup_f))
        if all_dups:
            raise ImportanceSelectionDuplicateError(all_dups)

        # Check selection length limits
        if len(priority_dimensions) > MAX_PRIORITY_DIMENSIONS:
            raise ImportanceSelectionTooManyPriorityError(len(priority_dimensions), MAX_PRIORITY_DIMENSIONS)

        if len(flexible_dimensions) > MAX_FLEXIBLE_DIMENSIONS:
            raise ImportanceSelectionTooManyFlexibleError(len(flexible_dimensions), MAX_FLEXIBLE_DIMENSIONS)

        # Check unknown dimensions
        valid_keys = set(CANONICAL_KEYS)
        unknown_keys = [k for k in (priority_dimensions + flexible_dimensions) if k not in valid_keys]
        if unknown_keys:
            raise ImportanceSelectionUnknownDimensionError(list(set(unknown_keys)))

        # Check overlap between priority and flexible
        p_set = set(priority_dimensions)
        f_set = set(flexible_dimensions)
        overlap = list(p_set.intersection(f_set))
        if overlap:
            raise ImportanceSelectionOverlapError(overlap)

        completion_mode = ImportanceCompletionModeEnum.EXPLICIT_SELECTION
        results = []
        for key in CANONICAL_KEYS:
            if key in p_set:
                level = ImportanceLevelEnum.PRIORITY
                weight = IMPORTANCE_LEVEL_WEIGHTS["PRIORITY"]
            elif key in f_set:
                level = ImportanceLevelEnum.FLEXIBLE
                weight = IMPORTANCE_LEVEL_WEIGHTS["FLEXIBLE"]
            else:
                level = ImportanceLevelEnum.STANDARD
                weight = IMPORTANCE_LEVEL_WEIGHTS["STANDARD"]

            results.append({
                "dimension_key": key,
                "level": level,
                "weight": weight
            })

        return completion_mode, results
