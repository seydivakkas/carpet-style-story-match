"""Pure deterministic Visual Style Match Engine v1.

Calculates weighted visual style match score and deterministic explanations between:
- Reviewed UserPreferenceProfile (final_value)
- ImportanceProfile (weight)
- CarpetStyleProfile (value, status)

CRITICAL INVARIANT:
CONFIDENCE IS NOT MULTIPLIED INTO THE MATCH SCORE.
Confidence metrics are read ONLY for explanation metadata.
"""
from typing import Dict, List, Any, Optional, Tuple
from app.domain.preferences.constants import CANONICAL_DIMENSIONS, DIMENSION_NAMES_TR
from app.db.models.preference_assessment import (
    StyleMatchStatusEnum,
    StyleMatchLabelEnum,
    ImportanceLevelEnum,
    UserPreferenceProvenanceEnum
)
from app.domain.stylematch.constants import (
    VISUAL_STYLE_MATCH_VERSION,
    MATCH_MIN_WEIGHTED_COVERAGE,
    MATCH_MIN_COMPARABLE_DIMENSIONS,
    get_match_label
)
from app.domain.stylematch.schemas import (
    StyleMatchDimensionResponse,
    StyleMatchExplanationMatch,
    StyleMatchExplanationDifference,
    StyleMatchExplanationResponse
)

class CalculatedMatchDimension:
    """Internal calculated values for a single canonical dimension."""
    def __init__(
        self,
        dimension_key: str,
        user_value: Optional[float],
        user_provenance: Optional[UserPreferenceProvenanceEnum],
        carpet_value: Optional[float],
        carpet_dimension_status: Optional[str],
        importance_level: ImportanceLevelEnum,
        importance_weight: float,
        difference: Optional[float],
        similarity: Optional[float],
        weighted_similarity: Optional[float],
        weighted_difference: Optional[float],
        comparable: bool,
        user_preference_confidence: Optional[float],
        carpet_measurement_confidence: Optional[float]
    ):
        self.dimension_key = dimension_key
        self.user_value = user_value
        self.user_provenance = user_provenance
        self.carpet_value = carpet_value
        self.carpet_dimension_status = carpet_dimension_status
        self.importance_level = importance_level
        self.importance_weight = importance_weight
        self.difference = difference
        self.similarity = similarity
        self.weighted_similarity = weighted_similarity
        self.weighted_difference = weighted_difference
        self.comparable = comparable
        self.user_preference_confidence = user_preference_confidence
        self.carpet_measurement_confidence = carpet_measurement_confidence

    @property
    def match_strength(self) -> float:
        """Weight * Similarity if comparable else 0.0."""
        if self.comparable and self.weighted_similarity is not None:
            return self.weighted_similarity
        return 0.0

    @property
    def mismatch_impact(self) -> float:
        """Weight * Difference if comparable else 0.0."""
        if self.comparable and self.weighted_difference is not None:
            return self.weighted_difference
        return 0.0

class CalculatedMatchResult:
    """Internal calculated match result bundle."""
    def __init__(
        self,
        match_version: str,
        status: StyleMatchStatusEnum,
        score: Optional[float],
        score_100: Optional[float],
        match_label: Optional[StyleMatchLabelEnum],
        comparable_dimension_count: int,
        weighted_coverage: float,
        total_importance_weight: float,
        comparable_weight: float,
        dimensions: List[CalculatedMatchDimension],
        explanation: StyleMatchExplanationResponse
    ):
        self.match_version = match_version
        self.status = status
        self.score = score
        self.score_100 = score_100
        self.match_label = match_label
        self.comparable_dimension_count = comparable_dimension_count
        self.weighted_coverage = weighted_coverage
        self.total_importance_weight = total_importance_weight
        self.comparable_weight = comparable_weight
        self.dimensions = dimensions
        self.explanation = explanation

class VisualStyleMatchEngine:
    """Pure deterministic Visual Style Match Engine."""

    @staticmethod
    def compute_match(
        user_dimensions_map: Dict[str, Dict[str, Any]],
        importance_dimensions_map: Dict[str, Dict[str, Any]],
        carpet_dimensions_map: Dict[str, Dict[str, Any]]
    ) -> CalculatedMatchResult:
        """
        Compute deterministic visual style match result.

        Args:
            user_dimensions_map: {dim_key: {"final_value": float, "provenance": Enum, "status": str, "confidence": float}}
            importance_dimensions_map: {dim_key: {"level": Enum, "weight": float}}
            carpet_dimensions_map: {dim_key: {"value": float, "status": str, "confidence": float}}
        """
        calculated_dimensions: List[CalculatedMatchDimension] = []
        total_importance_weight: float = 0.0
        comparable_weight: float = 0.0
        comparable_count: int = 0
        sum_weighted_similarity: float = 0.0

        for dim_key in CANONICAL_DIMENSIONS:
            user_dim = user_dimensions_map.get(dim_key, {})
            imp_dim = importance_dimensions_map.get(dim_key, {})
            carpet_dim = carpet_dimensions_map.get(dim_key, {})

            # 1. User values
            user_val = user_dim.get("final_value")
            user_status = user_dim.get("status", "MEASURED")
            user_provenance = user_dim.get("provenance")
            user_conf = user_dim.get("confidence")

            # 2. Importance values
            imp_level = imp_dim.get("level", ImportanceLevelEnum.STANDARD)
            imp_weight = float(imp_dim.get("weight", 0.60))

            total_importance_weight += imp_weight

            # 3. Carpet values
            carpet_val = carpet_dim.get("value")
            carpet_status = carpet_dim.get("status", "NOT_AVAILABLE")
            carpet_conf = carpet_dim.get("confidence")

            # 4. Check comparability
            user_valid = (user_status == "MEASURED" and user_val is not None)
            carpet_valid = (carpet_status in ["AVAILABLE", "LOW_CONFIDENCE"] and carpet_val is not None)
            is_comparable = (user_valid and carpet_valid)

            if is_comparable:
                diff = abs(float(user_val) - float(carpet_val))
                sim = 1.0 - diff
                w_sim = imp_weight * sim
                w_diff = imp_weight * diff

                comparable_count += 1
                comparable_weight += imp_weight
                sum_weighted_similarity += w_sim
            else:
                diff = None
                sim = None
                w_sim = None
                w_diff = None

            calc_dim = CalculatedMatchDimension(
                dimension_key=dim_key,
                user_value=user_val,
                user_provenance=user_provenance,
                carpet_value=carpet_val,
                carpet_dimension_status=carpet_status,
                importance_level=imp_level,
                importance_weight=imp_weight,
                difference=diff,
                similarity=sim,
                weighted_similarity=w_sim,
                weighted_difference=w_diff,
                comparable=is_comparable,
                user_preference_confidence=user_conf,
                carpet_measurement_confidence=carpet_conf
            )
            calculated_dimensions.append(calc_dim)

        # 5. Calculate coverage
        weighted_coverage = (comparable_weight / total_importance_weight) if total_importance_weight > 0 else 0.0

        # 6. Determine match status
        if comparable_count == 9:
            status = StyleMatchStatusEnum.COMPLETE
        elif comparable_count >= MATCH_MIN_COMPARABLE_DIMENSIONS and weighted_coverage >= MATCH_MIN_WEIGHTED_COVERAGE:
            status = StyleMatchStatusEnum.PARTIAL
        else:
            status = StyleMatchStatusEnum.NOT_AVAILABLE

        # 7. Calculate score
        if status in [StyleMatchStatusEnum.COMPLETE, StyleMatchStatusEnum.PARTIAL] and comparable_weight > 0:
            score = sum_weighted_similarity / comparable_weight
            # Bound check safety
            score = max(0.0, min(1.0, score))
            score_100 = score * 100.0
            match_label = get_match_label(score_100)
        else:
            score = None
            score_100 = None
            match_label = None

        # 8. Generate deterministic explanation
        explanation = VisualStyleMatchEngine._build_explanation(
            calculated_dimensions=calculated_dimensions,
            status=status,
            weighted_coverage=weighted_coverage,
            comparable_count=comparable_count
        )

        return CalculatedMatchResult(
            match_version=VISUAL_STYLE_MATCH_VERSION,
            status=status,
            score=score,
            score_100=score_100,
            match_label=match_label,
            comparable_dimension_count=comparable_count,
            weighted_coverage=weighted_coverage,
            total_importance_weight=total_importance_weight,
            comparable_weight=comparable_weight,
            dimensions=calculated_dimensions,
            explanation=explanation
        )

    @staticmethod
    def _build_explanation(
        calculated_dimensions: List[CalculatedMatchDimension],
        status: StyleMatchStatusEnum,
        weighted_coverage: float,
        comparable_count: int
    ) -> StyleMatchExplanationResponse:
        """Build deterministic explanation object."""
        top_matches: List[StyleMatchExplanationMatch] = []
        main_differences: List[StyleMatchExplanationDifference] = []
        coverage_notes: List[str] = []
        confidence_notes: List[str] = []

        comparable_dims = [d for d in calculated_dimensions if d.comparable]

        # Canonical dimension index mapping for tie-breaking
        canonical_indices = {key: idx for idx, key in enumerate(CANONICAL_DIMENSIONS)}

        # 1. Top Matches (Rank by match_strength desc, canonical idx asc)
        sorted_for_matches = sorted(
            comparable_dims,
            key=lambda d: (-d.match_strength, canonical_indices.get(d.dimension_key, 99))
        )

        for d in sorted_for_matches[:3]:
            if d.similarity is not None and d.similarity >= 0.50:
                dim_tr = DIMENSION_NAMES_TR.get(d.dimension_key, d.dimension_key)
                sim_pct = round(d.similarity * 100)
                narrative = f"{dim_tr} özelliğinde halı ile tercihleriniz yüksek oranda örtüşüyor (%{sim_pct} benzerlik)."
                top_matches.append(
                    StyleMatchExplanationMatch(
                        dimension_key=d.dimension_key,
                        similarity=d.similarity,
                        importance_level=d.importance_level,
                        importance_weight=d.importance_weight,
                        user_value=d.user_value or 0.0,
                        carpet_value=d.carpet_value or 0.0,
                        narrative=narrative
                    )
                )

        # 2. Main Differences (Rank by mismatch_impact desc, canonical idx asc)
        sorted_for_diffs = sorted(
            comparable_dims,
            key=lambda d: (-d.mismatch_impact, canonical_indices.get(d.dimension_key, 99))
        )

        for d in sorted_for_diffs[:2]:
            if d.difference is not None and d.difference >= 0.15:
                dim_tr = DIMENSION_NAMES_TR.get(d.dimension_key, d.dimension_key)
                if d.importance_level == ImportanceLevelEnum.PRIORITY:
                    narrative = f"{dim_tr} özelliğinde belirgin bir fark var; bu fark öncelikli tercihlerinizden birinde olduğu için genel uyumu daha fazla etkiliyor."
                elif d.importance_level == ImportanceLevelEnum.FLEXIBLE:
                    narrative = f"{dim_tr} özelliğinde belirgin bir fark var; ancak bu özellik esnek tercihleriniz arasında olduğu için etkisi sınırlı."
                else:
                    narrative = f"{dim_tr} özelliğinde orta düzey bir farklılık bulunuyor."

                main_differences.append(
                    StyleMatchExplanationDifference(
                        dimension_key=d.dimension_key,
                        difference=d.difference,
                        similarity=d.similarity or 0.0,
                        importance_level=d.importance_level,
                        importance_weight=d.importance_weight,
                        impact=d.mismatch_impact,
                        narrative=narrative
                    )
                )

        # 3. Coverage Notes
        if status == StyleMatchStatusEnum.PARTIAL:
            missing = [d.dimension_key for d in calculated_dimensions if not d.comparable]
            cov_pct = round(weighted_coverage * 100)
            missing_str = ", ".join(missing)
            coverage_notes.append(
                f"Kısmi stil uyumu hesaplandı (%{cov_pct} ağırlıklı kapsam). Karşılaştırılamayan boyutlar: {missing_str}."
            )
        elif status == StyleMatchStatusEnum.NOT_AVAILABLE:
            coverage_notes.append(
                f"Yetersiz halı stil verisi sebebiyle stil uyumu hesaplanamadı ({comparable_count}/9 boyut karşılaştırılabilir, minimum 6 boyut ve %70 ağırlıklı kapsam gereklidir)."
            )

        # 4. Confidence Notes (Explanatory annotation only)
        for d in calculated_dimensions:
            if d.comparable:
                dim_tr = DIMENSION_NAMES_TR.get(d.dimension_key, d.dimension_key)
                if d.carpet_dimension_status == "LOW_CONFIDENCE":
                    confidence_notes.append(
                        f"{dim_tr} boyutunda halı görsel analizi düşük güvenilirliktedir (Ölçüm güvenliği: {d.carpet_measurement_confidence or 0.0:.2f})."
                    )
                elif d.user_preference_confidence is not None and d.user_preference_confidence < 0.40:
                    confidence_notes.append(
                        f"{dim_tr} boyutunda kullanıcı tercihi düşük güvenilirliktedir (Tercih güvenliği: {d.user_preference_confidence:.2f})."
                    )

        return StyleMatchExplanationResponse(
            top_matches=top_matches,
            main_differences=main_differences,
            coverage_notes=coverage_notes,
            confidence_notes=confidence_notes
        )
