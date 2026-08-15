from typing import Dict, List, Any
from app.db.models.preference_assessment import PreferenceDimensionStatus
from app.domain.contracts import CANONICAL_STYLE_DNA
from app.domain.preferences.constants import (
    TEXT_EVIDENCE_MATRIX_WEIGHTS,
    VISUAL_EVIDENCE_MATRIX_WEIGHTS
)

CANONICAL_KEYS = [d["key"] for d in CANONICAL_STYLE_DNA]

class TextPreferenceAggregator:
    """Pure, deterministic matrix aggregator mapping 6 text responses to canonical 9D preference scores."""

    @staticmethod
    def aggregate(responses: Dict[str, float]) -> List[Dict[str, Any]]:
        dim_results = []

        for dim_idx, dim_key in enumerate(CANONICAL_KEYS):
            total_weight = 0.0
            weighted_sum = 0.0
            evidence_count = 0

            for q_key, w_list in TEXT_EVIDENCE_MATRIX_WEIGHTS.items():
                w = w_list[dim_idx]
                if w > 0.0 and q_key in responses:
                    r_val = responses[q_key]
                    total_weight += w
                    weighted_sum += r_val * w
                    evidence_count += 1

            if total_weight == 0.0:
                dim_results.append({
                    "dimension_key": dim_key,
                    "value": None,
                    "status": PreferenceDimensionStatus.NOT_MEASURED,
                    "evidence_weight": 0.0,
                    "evidence_count": 0
                })
            else:
                directional_avg = weighted_sum / total_weight
                pref_value = (directional_avg + 1.0) / 2.0
                pref_value_clamped = float(max(0.0, min(1.0, pref_value)))

                dim_results.append({
                    "dimension_key": dim_key,
                    "value": round(pref_value_clamped, 4),
                    "status": PreferenceDimensionStatus.MEASURED,
                    "evidence_weight": round(total_weight, 2),
                    "evidence_count": evidence_count
                })

        return dim_results

class VisualPreferenceAggregator:
    """Pure, deterministic matrix aggregator mapping 6 visual canonical directions to 9D preference scores."""

    @staticmethod
    def aggregate(canonical_directions: Dict[str, float]) -> List[Dict[str, Any]]:
        dim_results = []

        for dim_idx, dim_key in enumerate(CANONICAL_KEYS):
            total_weight = 0.0
            weighted_sum = 0.0
            evidence_count = 0

            for card_key, w_list in VISUAL_EVIDENCE_MATRIX_WEIGHTS.items():
                w = w_list[dim_idx]
                if w > 0.0 and card_key in canonical_directions:
                    c_val = canonical_directions[card_key]
                    total_weight += w
                    weighted_sum += c_val * w
                    evidence_count += 1

            if total_weight == 0.0:
                dim_results.append({
                    "dimension_key": dim_key,
                    "value": None,
                    "status": PreferenceDimensionStatus.NOT_MEASURED,
                    "evidence_weight": 0.0,
                    "evidence_count": 0
                })
            else:
                directional_avg = weighted_sum / total_weight
                pref_value = (directional_avg + 1.0) / 2.0
                pref_value_clamped = float(max(0.0, min(1.0, pref_value)))

                dim_results.append({
                    "dimension_key": dim_key,
                    "value": round(pref_value_clamped, 4),
                    "status": PreferenceDimensionStatus.MEASURED,
                    "evidence_weight": round(total_weight, 2),
                    "evidence_count": evidence_count
                })

        return dim_results
