"""Pure comparison engine for Historical Connection Engine v1."""
from typing import Dict, List, Any
from app.db.models.carpet_historical_connection import (
    HistoricalConnectionStatusEnum,
    HistoricalConnectionNotAvailableReasonEnum,
    HistoricalConnectionLevelEnum
)
from app.domain.historical_connection.constants import HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS


class HistoricalConnectionEngine:
    """Pure comparison engine for pairwise 9-D Style DNA visual proximity."""

    CANONICAL_DIMENSIONS = [
        "color_energy",
        "color_diversity",
        "contrast",
        "warmth",
        "visual_complexity",
        "structural_order",
        "rhythm_repetition",
        "focal_strength",
        "form_language"
    ]

    COMPARABLE_STATUSES = {"AVAILABLE", "LOW_CONFIDENCE"}

    @classmethod
    def evaluate(
        cls,
        target_dimensions: List[Any],
        reference_dimensions: List[Any]
    ) -> Dict[str, Any]:
        target_map = {d.dimension_key: d for d in target_dimensions}
        ref_map = {d.dimension_key: d for d in reference_dimensions}

        dimension_snapshots = []
        comparable_count = 0

        for key in cls.CANONICAL_DIMENSIONS:
            t_dim = target_map.get(key)
            r_dim = ref_map.get(key)

            t_val = getattr(t_dim, "value", None) if t_dim else None
            t_stat = getattr(t_dim, "status", None) if t_dim else "NOT_AVAILABLE"
            t_stat_val = t_stat.value if hasattr(t_stat, "value") else str(t_stat)
            t_conf = getattr(t_dim, "confidence_score", None) if t_dim else None

            r_val = getattr(r_dim, "value", None) if r_dim else None
            r_stat = getattr(r_dim, "status", None) if r_dim else "NOT_AVAILABLE"
            r_stat_val = r_stat.value if hasattr(r_stat, "value") else str(r_stat)
            r_conf = getattr(r_dim, "confidence_score", None) if r_dim else None

            is_comparable = (
                t_stat_val in cls.COMPARABLE_STATUSES
                and t_val is not None
                and r_stat_val in cls.COMPARABLE_STATUSES
                and r_val is not None
            )

            if is_comparable:
                diff = abs(float(t_val) - float(r_val))
                sim = 1.0 - diff
                comparable_count += 1
            else:
                diff = None
                sim = None

            dimension_snapshots.append({
                "dimension_key": key,
                "target_value": float(t_val) if t_val is not None else None,
                "target_status": t_stat_val,
                "target_confidence": float(t_conf) if t_conf is not None else None,
                "reference_value": float(r_val) if r_val is not None else None,
                "reference_status": r_stat_val,
                "reference_confidence": float(r_conf) if r_conf is not None else None,
                "difference": round(diff, 4) if diff is not None else None,
                "similarity": round(sim, 4) if sim is not None else None,
                "comparable": is_comparable
            })

        coverage = round(comparable_count / 9.0, 4)

        if comparable_count >= HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS:
            status = HistoricalConnectionStatusEnum.COMPLETE if comparable_count == 9 else HistoricalConnectionStatusEnum.PARTIAL
            not_available_reason = None

            sum_sim = sum(d["similarity"] for d in dimension_snapshots if d["comparable"])
            style_similarity = round(sum_sim / float(comparable_count), 4)

            if style_similarity >= 0.90:
                connection_level = HistoricalConnectionLevelEnum.VERY_CLOSE
            elif style_similarity >= 0.75:
                connection_level = HistoricalConnectionLevelEnum.CLOSE
            elif style_similarity >= 0.60:
                connection_level = HistoricalConnectionLevelEnum.MODERATE
            else:
                connection_level = HistoricalConnectionLevelEnum.LIMITED
        else:
            status = HistoricalConnectionStatusEnum.NOT_AVAILABLE
            not_available_reason = HistoricalConnectionNotAvailableReasonEnum.INSUFFICIENT_COMPARABLE_DIMENSIONS
            style_similarity = None
            connection_level = None

        return {
            "status": status,
            "not_available_reason": not_available_reason,
            "style_similarity": style_similarity,
            "connection_level": connection_level,
            "comparable_dimension_count": comparable_count,
            "dimension_coverage": coverage,
            "dimensions": dimension_snapshots
        }
