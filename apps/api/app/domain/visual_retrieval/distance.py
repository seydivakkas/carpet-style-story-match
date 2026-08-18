"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Deterministic 9D Style DNA Distance and Proximity Engine v1.0.0
"""
import math
from typing import Dict, List, Tuple, Optional
from app.domain.visual_retrieval.models import (
    CANONICAL_DIMENSION_KEYS,
    StyleDimensionDelta,
)


def compute_9d_distance_and_score(
    query_vector: Dict[str, float],
    candidate_vector: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, float, List[StyleDimensionDelta], List[str], List[str]]:
    """
    Computes normalized 9D weighted Euclidean distance, proximity score [0, 100],
    per-dimension deltas, top 3 closest dimensions, and top 2 largest differences.

    Invariants:
    - Canonical dimension ordering is strictly enforced.
    - Default weights are equal (1.0) across all 9 dimensions.
    - Proximity score: score = 100 * (1 - normalized_distance).
    - Identical vectors return score = 100.0, distance = 0.0.
    """
    if weights is None:
        effective_weights = {k: 1.0 for k in CANONICAL_DIMENSION_KEYS}
    else:
        effective_weights = {k: float(weights.get(k, 1.0)) for k in CANONICAL_DIMENSION_KEYS}

    sum_weighted_sq_diff = 0.0
    sum_weights = 0.0
    deltas: List[StyleDimensionDelta] = []

    for k in CANONICAL_DIMENSION_KEYS:
        q_val = float(query_vector[k])
        c_val = float(candidate_vector[k])
        w = effective_weights[k]

        abs_delta = abs(q_val - c_val)
        norm_delta = abs_delta  # Since dimensions are normalized [0.0, 1.0]

        sum_weighted_sq_diff += w * (abs_delta ** 2)
        sum_weights += w

        deltas.append(
            StyleDimensionDelta(
                dimension_key=k,
                query_value=round(q_val, 4),
                candidate_value=round(c_val, 4),
                absolute_delta=round(abs_delta, 4),
                normalized_delta=round(norm_delta, 4),
            )
        )

    if sum_weights <= 0.0:
        sum_weights = 1.0

    normalized_distance = math.sqrt(sum_weighted_sq_diff / sum_weights)
    # Clamp distance to [0.0, 1.0]
    normalized_distance = max(0.0, min(1.0, normalized_distance))

    raw_score = 100.0 * (1.0 - normalized_distance)
    proximity_score = max(0.0, min(100.0, raw_score))

    # Sort deltas for explainability
    # Closest: smallest absolute_delta, secondary sort key alphabetically for deterministic tie break
    sorted_closest = sorted(deltas, key=lambda d: (d.absolute_delta, d.dimension_key))
    closest_dimensions = [d.dimension_key for d in sorted_closest[:3]]

    # Largest diffs: largest absolute_delta, secondary sort key alphabetically for deterministic tie break
    sorted_largest = sorted(deltas, key=lambda d: (-d.absolute_delta, d.dimension_key))
    largest_differences = [d.dimension_key for d in sorted_largest[:2]]

    return (
        round(normalized_distance, 6),
        round(proximity_score, 2),
        deltas,
        closest_dimensions,
        largest_differences,
    )
