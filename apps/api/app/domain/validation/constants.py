"""Validation Domain Constants for Carpet Style & Story Match v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

VALIDATION_BENCHMARK_VERSION = "validation-benchmark-v1"
RELEASE_CONTRACT_VERSION = "release-contract-v1"

# Canonical Subsystem Version Inventory
VERSION_INVENTORY = {
    "style_dna": "style-dna-v1.0.0",
    "text_preference_evidence": "text-preference-evidence-v1",
    "visual_preference_stimuli": "visual-preference-stimuli-v1",
    "visual_preference_evidence": "visual-preference-evidence-v1",
    "multimodal_preference": "multimodal-preference-v1",
    "preference_confidence": "preference-confidence-v1",
    "importance": "importance-v1",
    "visual_style_match": "visual-style-match-v1",
    "user_narrative_profile": "user-narrative-profile-v1",
    "motif_story_knowledge": "motif-story-knowledge-v1",
    "carpet_catalog_curation": "carpet-catalog-curation-v1",
    "narrative_affinity": "narrative-affinity-v1",
    "historical_reference": "historical-reference-v1",
    "historical_connection": "historical-connection-v1",
    "frontend_experience": "frontend-experience-v1"
}

# Style DNA Determinism Tolerance
STYLE_DNA_DETERMINISM_TOLERANCE = 1e-4

# Visual Stimuli Validation Thresholds
STIMULUS_MIN_TARGET_DELTA = 0.35
STIMULUS_MAX_NON_TARGET_CONTAMINATION = 0.15

# Visual Style Match Thresholds
STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS = 6
STYLE_MATCH_MIN_WEIGHTED_COVERAGE = 0.70

# Visual Style Match Label Boundaries (score_100)
STYLE_MATCH_LABEL_BOUNDARIES = {
    "VERY_HIGH": 90.0,
    "HIGH": 75.0,
    "MODERATE": 60.0,
    "LOW": 45.0
}

# Narrative Affinity Threshold Boundaries (coverage)
NARRATIVE_AFFINITY_BOUNDARIES = {
    "VERY_STRONG": 0.80,
    "STRONG": 0.60,
    "MODERATE": 0.35,
    "LIMITED": 0.0
}

# Historical Connection Threshold Boundaries (style_similarity)
HISTORICAL_CONNECTION_BOUNDARIES = {
    "VERY_CLOSE": 0.90,
    "CLOSE": 0.75,
    "MODERATE": 0.60,
    "LIMITED": 0.0
}
HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS = 6

# Visual Stimuli Asset SHA-256 Hashes
STIMULI_ASSET_HASHES = {
    "v1_color_energy_a.svg": "36422f92d374ebfc84f2ed7a74ee2ff1c1d4d0d1152f99f0d59acea06af6747a",
    "v1_color_energy_b.svg": "fceff54c8e4529cc1eee7ad558f2696f6c33cf34c87e9363c18863ccab1f4cab",
    "v2_contrast_a.svg": "f5f964612cbdf7744ff0b4f9251fb1e1f15e33809cc771c10b032a9be4575677",
    "v2_contrast_b.svg": "11d182175fab9ddafabae8c310ae84eccd0c01b365459f40538e1386b403dcb8",
    "v3_visual_complexity_a.svg": "c181d953051a88811de34da3d9fb186c85ca0ff2ba754c94174a649fa05495f7",
    "v3_visual_complexity_b.svg": "b896982ed5fe4e5f5ea6f596d67c90caeb3a8ab55a3a08599d65dff6b6fe8994",
    "v4_structural_order_a.svg": "77c8bad3ccf96944ae2ad1cf02c9185aeb0ea2caa7361d42d4ed71fdb4b6eaae",
    "v4_structural_order_b.svg": "f867720040889344798e61827238d449f993a9bd9d2f13a290a8d4b6680b1874",
    "v5_rhythm_repetition_a.svg": "79f5cccf74630077d16242880c94cc431502f8fb9db05418f87ad1ec84bf6a8b",
    "v5_rhythm_repetition_b.svg": "d0747b8f7ea25120ffd1d4e70a6b09b3d76ebaa7674671f8539a10f48dec2a87",
    "v6_form_language_a.svg": "42a87b530c935359207111654c8dc31783e80b63ed7cf7c908216e1bfc1551cb",
    "v6_form_language_b.svg": "8f55af132a95a42965413d7bed4ffab1ce4302b0683681c2ade2cf4a04791a3d"
}
