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

class MultimodalPreferenceAggregator:
    """Pure, deterministic multimodal aggregator merging TextPreferenceProfile and VisualPreferenceProfile into 9D UserPreferenceProfile."""

    @staticmethod
    def aggregate(
        text_dims: Dict[str, Dict[str, Any]],
        visual_dims: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        from app.db.models.preference_assessment import UserPreferenceProvenanceEnum

        dim_results = []

        for dim_key in CANONICAL_KEYS:
            t_dim = text_dims.get(dim_key, {})
            v_dim = visual_dims.get(dim_key, {})

            t_val = t_dim.get("value")
            t_status = t_dim.get("status", PreferenceDimensionStatus.NOT_MEASURED)
            t_weight = t_dim.get("evidence_weight", 0.0) if t_status == PreferenceDimensionStatus.MEASURED else 0.0

            v_val = v_dim.get("value")
            v_status = v_dim.get("status", PreferenceDimensionStatus.NOT_MEASURED)
            v_weight = v_dim.get("evidence_weight", 0.0) if v_status == PreferenceDimensionStatus.MEASURED else 0.0

            t_measured = (t_status == PreferenceDimensionStatus.MEASURED and t_val is not None)
            v_measured = (v_status == PreferenceDimensionStatus.MEASURED and v_val is not None)

            if t_measured and v_measured:
                total_w = t_weight + v_weight
                if total_w > 0.0:
                    inferred_val = (t_val * t_weight + v_val * v_weight) / total_w
                else:
                    inferred_val = (t_val + v_val) / 2.0
                inferred_val = float(max(0.0, min(1.0, inferred_val)))
                status = PreferenceDimensionStatus.MEASURED
            elif t_measured:
                inferred_val = float(max(0.0, min(1.0, t_val)))
                status = PreferenceDimensionStatus.MEASURED
            elif v_measured:
                inferred_val = float(max(0.0, min(1.0, v_val)))
                status = PreferenceDimensionStatus.MEASURED
            else:
                inferred_val = None
                status = PreferenceDimensionStatus.NOT_MEASURED

            inferred_rounded = round(inferred_val, 4) if inferred_val is not None else None

            dim_results.append({
                "dimension_key": dim_key,
                "inferred_value": inferred_rounded,
                "final_value": inferred_rounded,
                "status": status,
                "provenance": UserPreferenceProvenanceEnum.INFERRED,
                "text_value": round(t_val, 4) if t_val is not None else None,
                "text_evidence_weight": round(t_weight, 2),
                "visual_value": round(v_val, 4) if v_val is not None else None,
                "visual_evidence_weight": round(v_weight, 2),
            })

        return dim_results

class PreferenceConfidenceCalculator:
    """Pure, deterministic confidence calculator for 9D user preference profiles."""

    @staticmethod
    def calculate(
        text_dims: Dict[str, Dict[str, Any]],
        visual_dims: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        import json
        from app.db.models.preference_assessment import ConfidenceStatusEnum

        results = []

        for dim_key in CANONICAL_KEYS:
            t_dim = text_dims.get(dim_key, {})
            v_dim = visual_dims.get(dim_key, {})

            t_val = t_dim.get("value")
            t_status = t_dim.get("status", PreferenceDimensionStatus.NOT_MEASURED)
            t_weight = t_dim.get("evidence_weight", 0.0) if t_status == PreferenceDimensionStatus.MEASURED else 0.0

            v_val = v_dim.get("value")
            v_status = v_dim.get("status", PreferenceDimensionStatus.NOT_MEASURED)
            v_weight = v_dim.get("evidence_weight", 0.0) if v_status == PreferenceDimensionStatus.MEASURED else 0.0

            t_measured = (t_status == PreferenceDimensionStatus.MEASURED and t_val is not None)
            v_measured = (v_status == PreferenceDimensionStatus.MEASURED and v_val is not None)

            t_strength = min(t_weight, 1.0) if t_measured else 0.0
            v_strength = min(v_weight, 1.0) if v_measured else 0.0

            if t_measured and v_measured:
                modality_count = 2
                source_coverage = (t_strength + v_strength) / 2.0
                agreement = 1.0 - abs(t_val - v_val)
                raw_conf = 0.25 * source_coverage + 0.75 * agreement
                conf_clamped = float(max(0.0, min(1.0, raw_conf)))
                status = ConfidenceStatusEnum.AVAILABLE
                conf_final = round(conf_clamped, 4)
                agreement_final = round(agreement, 4)
                coverage_final = round(source_coverage, 4)
            elif t_measured or v_measured:
                modality_count = 1
                source_strength = t_strength if t_measured else v_strength
                agreement_final = None
                coverage_final = round(source_strength, 4)
                raw_conf = 0.60 * source_strength
                conf_clamped = float(max(0.0, min(1.0, raw_conf)))
                status = ConfidenceStatusEnum.AVAILABLE
                conf_final = round(conf_clamped, 4)
            else:
                modality_count = 0
                agreement_final = None
                coverage_final = 0.0
                conf_final = None
                status = ConfidenceStatusEnum.NO_EVIDENCE

            evidence_dict = {
                "text_value": round(t_val, 4) if t_val is not None else None,
                "text_weight": round(t_weight, 2),
                "visual_value": round(v_val, 4) if v_val is not None else None,
                "visual_weight": round(v_weight, 2),
                "modality_count": modality_count,
                "agreement": agreement_final,
                "source_coverage": coverage_final,
            }

            results.append({
                "dimension_key": dim_key,
                "confidence": conf_final,
                "status": status,
                "modality_count": modality_count,
                "agreement": agreement_final,
                "source_coverage": coverage_final,
                "evidence_json": json.dumps(evidence_dict)
            })

        return results
