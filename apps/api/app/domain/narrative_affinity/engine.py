"""Pure calculation engine for Explainable Narrative Affinity v1."""
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Tuple
from app.db.models.carpet import CarpetSourceType
from app.db.models.carpet_story_association import CarpetStoryAssociationModel
from app.db.models.preference_assessment import (
    UserNarrativeProfileModel,
    NarrativeCompletionModeEnum,
    NarrativeInterestLevelEnum
)
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityStatusEnum,
    NarrativeAffinityLevelEnum,
    NarrativeNotAvailableReasonEnum,
    ThemeSupportStatusEnum
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.narrative_affinity.constants import (
    NARRATIVE_AFFINITY_VERSION,
    THRESHOLD_VERY_STRONG,
    THRESHOLD_STRONG,
    THRESHOLD_MODERATE
)
from app.domain.narrative_affinity.exceptions import NarrativeAffinityRequiresCatalogCarpetError
from app.domain.narrative_affinity.projector import CarpetNarrativeEvidenceProjector, ThemeSupportProjection


@dataclass
class EngineThemeSnapshot:
    theme_key: str
    user_interest_level: NarrativeInterestLevelEnum
    user_interest_weight: float
    user_selected: bool
    carpet_support_status: ThemeSupportStatusEnum
    confirmed_match: bool
    contested_overlap: bool
    has_contested_evidence: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    story_associations: List[CarpetStoryAssociationModel] = field(default_factory=list)


@dataclass
class EngineAffinityOutput:
    affinity_version: str
    status: NarrativeAffinityStatusEnum
    not_available_reason: Optional[NarrativeNotAvailableReasonEnum]
    affinity_level: Optional[NarrativeAffinityLevelEnum]
    confirmed_interest_coverage: Optional[float]
    selected_theme_count: int
    selected_interest_weight: float
    confirmed_matched_theme_count: int
    confirmed_matched_interest_weight: float
    contested_overlap_count: int
    theme_snapshots: List[EngineThemeSnapshot]


class NarrativeAffinityEngine:
    """Pure calculation engine for Narrative Affinity v1."""

    @classmethod
    def calculate_affinity(
        cls,
        user_narrative_profile: UserNarrativeProfileModel,
        carpet_source_type: CarpetSourceType,
        story_associations: List[CarpetStoryAssociationModel]
    ) -> EngineAffinityOutput:
        # Precondition check: Must be catalog carpet
        if carpet_source_type != CarpetSourceType.CATALOG:
            raise NarrativeAffinityRequiresCatalogCarpetError(
                f"Narrative affinity requires catalog carpet (got {carpet_source_type})"
            )

        # Build user theme interest map in N1..N8 order
        user_theme_map: Dict[str, Tuple[NarrativeInterestLevelEnum, float]] = {}
        if user_narrative_profile.themes:
            for ut in user_narrative_profile.themes:
                level = ut.interest_level
                weight = 1.0 if level == NarrativeInterestLevelEnum.PRIMARY else (0.6 if level == NarrativeInterestLevelEnum.SECONDARY else 0.0)
                user_theme_map[ut.theme_key] = (level, weight)

        # Fill missing canonical themes as NOT_SELECTED
        for t in CANONICAL_NARRATIVE_THEMES:
            k = t["key"]
            if k not in user_theme_map:
                user_theme_map[k] = (NarrativeInterestLevelEnum.NOT_SELECTED, 0.0)

        # Check user skipped
        if user_narrative_profile.completion_mode == NarrativeCompletionModeEnum.SKIPPED:
            theme_snapshots = cls._build_snapshots(user_theme_map, {}, is_not_available=True)
            return EngineAffinityOutput(
                affinity_version=NARRATIVE_AFFINITY_VERSION,
                status=NarrativeAffinityStatusEnum.NOT_AVAILABLE,
                not_available_reason=NarrativeNotAvailableReasonEnum.USER_NARRATIVE_SKIPPED,
                affinity_level=None,
                confirmed_interest_coverage=None,
                selected_theme_count=0,
                selected_interest_weight=0.0,
                confirmed_matched_theme_count=0,
                confirmed_matched_interest_weight=0.0,
                contested_overlap_count=0,
                theme_snapshots=theme_snapshots
            )

        # Calculate selected interest weight
        selected_themes = [k for k, (lvl, w) in user_theme_map.items() if w > 0]
        selected_interest_weight = sum(w for _, w in user_theme_map.values() if w > 0)
        selected_theme_count = len(selected_themes)

        if selected_interest_weight == 0:
            theme_snapshots = cls._build_snapshots(user_theme_map, {}, is_not_available=True)
            return EngineAffinityOutput(
                affinity_version=NARRATIVE_AFFINITY_VERSION,
                status=NarrativeAffinityStatusEnum.NOT_AVAILABLE,
                not_available_reason=NarrativeNotAvailableReasonEnum.NO_SELECTED_USER_THEMES,
                affinity_level=None,
                confirmed_interest_coverage=None,
                selected_theme_count=0,
                selected_interest_weight=0.0,
                confirmed_matched_theme_count=0,
                confirmed_matched_interest_weight=0.0,
                contested_overlap_count=0,
                theme_snapshots=theme_snapshots
            )

        # Project carpet evidence to N1..N8
        evidence_projections = CarpetNarrativeEvidenceProjector.project_evidence(story_associations)

        # Count carpet evidence states
        total_carpet_evidence_count = sum(
            1 for proj in evidence_projections.values() if proj.carpet_support_status != ThemeSupportStatusEnum.NO_EVIDENCE
        )
        confirmed_carpet_evidence_count = sum(
            1 for proj in evidence_projections.values() if proj.carpet_support_status in (ThemeSupportStatusEnum.DOCUMENTED, ThemeSupportStatusEnum.CONTEXTUAL)
        )
        contested_only_carpet_evidence_count = sum(
            1 for proj in evidence_projections.values() if proj.carpet_support_status == ThemeSupportStatusEnum.CONTESTED_ONLY
        )

        if total_carpet_evidence_count == 0:
            theme_snapshots = cls._build_snapshots(user_theme_map, evidence_projections, is_not_available=True)
            return EngineAffinityOutput(
                affinity_version=NARRATIVE_AFFINITY_VERSION,
                status=NarrativeAffinityStatusEnum.NOT_AVAILABLE,
                not_available_reason=NarrativeNotAvailableReasonEnum.NO_CARPET_NARRATIVE_THEME_EVIDENCE,
                affinity_level=None,
                confirmed_interest_coverage=None,
                selected_theme_count=selected_theme_count,
                selected_interest_weight=selected_interest_weight,
                confirmed_matched_theme_count=0,
                confirmed_matched_interest_weight=0.0,
                contested_overlap_count=0,
                theme_snapshots=theme_snapshots
            )

        if confirmed_carpet_evidence_count == 0 and contested_only_carpet_evidence_count > 0:
            theme_snapshots = cls._build_snapshots(user_theme_map, evidence_projections, is_not_available=True)
            return EngineAffinityOutput(
                affinity_version=NARRATIVE_AFFINITY_VERSION,
                status=NarrativeAffinityStatusEnum.NOT_AVAILABLE,
                not_available_reason=NarrativeNotAvailableReasonEnum.ONLY_CONTESTED_CARPET_EVIDENCE,
                affinity_level=None,
                confirmed_interest_coverage=None,
                selected_theme_count=selected_theme_count,
                selected_interest_weight=selected_interest_weight,
                confirmed_matched_theme_count=0,
                confirmed_matched_interest_weight=0.0,
                contested_overlap_count=0,
                theme_snapshots=theme_snapshots
            )

        # Calculate AVAILABLE Narrative Affinity
        theme_snapshots = cls._build_snapshots(user_theme_map, evidence_projections, is_not_available=False)

        confirmed_matched_theme_count = sum(1 for s in theme_snapshots if s.confirmed_match)
        confirmed_matched_interest_weight = sum(s.user_interest_weight for s in theme_snapshots if s.confirmed_match)
        contested_overlap_count = sum(1 for s in theme_snapshots if s.contested_overlap)

        coverage = confirmed_matched_interest_weight / selected_interest_weight
        coverage = round(coverage, 4)

        if coverage >= THRESHOLD_VERY_STRONG:
            level = NarrativeAffinityLevelEnum.VERY_STRONG
        elif coverage >= THRESHOLD_STRONG:
            level = NarrativeAffinityLevelEnum.STRONG
        elif coverage >= THRESHOLD_MODERATE:
            level = NarrativeAffinityLevelEnum.MODERATE
        else:
            level = NarrativeAffinityLevelEnum.LIMITED

        return EngineAffinityOutput(
            affinity_version=NARRATIVE_AFFINITY_VERSION,
            status=NarrativeAffinityStatusEnum.AVAILABLE,
            not_available_reason=None,
            affinity_level=level,
            confirmed_interest_coverage=coverage,
            selected_theme_count=selected_theme_count,
            selected_interest_weight=selected_interest_weight,
            confirmed_matched_theme_count=confirmed_matched_theme_count,
            confirmed_matched_interest_weight=confirmed_matched_interest_weight,
            contested_overlap_count=contested_overlap_count,
            theme_snapshots=theme_snapshots
        )

    @classmethod
    def _build_snapshots(
        cls,
        user_theme_map: Dict[str, Tuple[NarrativeInterestLevelEnum, float]],
        evidence_projections: Dict[str, ThemeSupportProjection],
        is_not_available: bool
    ) -> List[EngineThemeSnapshot]:
        snapshots: List[EngineThemeSnapshot] = []

        for t in CANONICAL_NARRATIVE_THEMES:
            k = t["key"]
            lvl, w = user_theme_map.get(k, (NarrativeInterestLevelEnum.NOT_SELECTED, 0.0))
            is_selected = w > 0

            proj = evidence_projections.get(k)
            support_status = proj.carpet_support_status if proj else ThemeSupportStatusEnum.NO_EVIDENCE
            has_contested = proj.has_contested_evidence if proj else False
            ev_dict = proj.to_evidence_dict() if proj else {
                "documented_claim_keys": [],
                "contextual_claim_keys": [],
                "contested_claim_keys": [],
                "story_association_ids": []
            }
            story_assocs = proj.story_associations if proj else []

            if is_not_available:
                confirmed_match = False
                contested_overlap = False
            else:
                confirmed_match = is_selected and (support_status in (ThemeSupportStatusEnum.DOCUMENTED, ThemeSupportStatusEnum.CONTEXTUAL))
                contested_overlap = is_selected and (support_status == ThemeSupportStatusEnum.CONTESTED_ONLY or has_contested)

            snapshots.append(
                EngineThemeSnapshot(
                    theme_key=k,
                    user_interest_level=lvl,
                    user_interest_weight=w,
                    user_selected=is_selected,
                    carpet_support_status=support_status,
                    confirmed_match=confirmed_match,
                    contested_overlap=contested_overlap,
                    has_contested_evidence=has_contested,
                    evidence=ev_dict,
                    story_associations=story_assocs
                )
            )

        return snapshots
