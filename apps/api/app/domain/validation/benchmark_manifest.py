"""Validation Benchmark Manifest for Carpet Style & Story Match v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import Any, Dict
from app.domain.validation.constants import (
    HISTORICAL_CONNECTION_BOUNDARIES,
    HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS,
    NARRATIVE_AFFINITY_BOUNDARIES,
    RELEASE_CONTRACT_VERSION,
    STIMULI_ASSET_HASHES,
    STIMULUS_MAX_NON_TARGET_CONTAMINATION,
    STIMULUS_MIN_TARGET_DELTA,
    STYLE_DNA_DETERMINISM_TOLERANCE,
    STYLE_MATCH_LABEL_BOUNDARIES,
    STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS,
    STYLE_MATCH_MIN_WEIGHTED_COVERAGE,
    VALIDATION_BENCHMARK_VERSION,
    VERSION_INVENTORY,
)

BENCHMARK_MANIFEST: Dict[str, Any] = {
    "manifest_version": "v1.0.0",
    "benchmark_version": VALIDATION_BENCHMARK_VERSION,
    "release_contract_version": RELEASE_CONTRACT_VERSION,
    "subsystem_versions": VERSION_INVENTORY,
    "thresholds": {
        "style_dna_determinism_tolerance": STYLE_DNA_DETERMINISM_TOLERANCE,
        "visual_stimulus": {
            "min_target_delta": STIMULUS_MIN_TARGET_DELTA,
            "max_non_target_contamination": STIMULUS_MAX_NON_TARGET_CONTAMINATION,
        },
        "visual_style_match": {
            "min_comparable_dimensions": STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS,
            "min_weighted_coverage": STYLE_MATCH_MIN_WEIGHTED_COVERAGE,
            "label_boundaries": STYLE_MATCH_LABEL_BOUNDARIES,
        },
        "narrative_affinity": {
            "label_boundaries": NARRATIVE_AFFINITY_BOUNDARIES,
        },
        "historical_connection": {
            "min_comparable_dimensions": HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS,
            "label_boundaries": HISTORICAL_CONNECTION_BOUNDARIES,
        },
    },
    "stimuli_hashes": STIMULI_ASSET_HASHES,
    "golden_cases": {
        "visual_style_match": {
            "exact_match_score": 1.0,
            "opposite_match_score": 0.0,
        },
        "narrative_affinity": {
            "n1_primary_n2_secondary_carpet_n2_only": 0.375,  # 0.6 / (1.0 + 0.6)
        },
        "historical_connection": {
            "exact_match_similarity": 1.0,
            "opposite_match_similarity": 0.0,
        },
    },
    "known_limitations": [
        "Style DNA is model-free/full-image v1 using deterministic CV heuristics.",
        "D9 is geometry-based form language, not botanical motif recognition.",
        "D8 is visual energy concentration, not eye tracking.",
        "User D8 evidence is weak text-only (weight 0.25).",
        "Narrative knowledge requires explicit human curation and provenance.",
        "Narrative Affinity is not universal motif meaning validation.",
        "Historical Connection is visual proximity, not historical attribution/authentication.",
        "No recommendation ranking engine is implemented or claimed."
    ]
}
