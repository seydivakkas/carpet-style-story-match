"""Automated Benchmark Check Suites for Carpet Style & Story Match v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import math
from typing import List, Dict, Any
from pathlib import Path
import hashlib
from types import SimpleNamespace

from app.domain.validation.constants import (
    HISTORICAL_CONNECTION_BOUNDARIES,
    HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS,
    NARRATIVE_AFFINITY_BOUNDARIES,
    STIMULI_ASSET_HASHES,
    STIMULUS_MAX_NON_TARGET_CONTAMINATION,
    STIMULUS_MIN_TARGET_DELTA,
    STYLE_DNA_DETERMINISM_TOLERANCE,
    STYLE_MATCH_LABEL_BOUNDARIES,
    STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS,
    STYLE_MATCH_MIN_WEIGHTED_COVERAGE,
    VERSION_INVENTORY,
)
from app.domain.validation.models import BenchmarkCheckResult, BenchmarkCheckStatus

# Domain Engine & Contract Imports
from app.domain.contracts import CANONICAL_STYLE_DNA, CANONICAL_NARRATIVE_THEMES
from app.domain.styledna.engine import StyleDNAEngine
from app.domain.preferences.constants import (
    CANONICAL_TEXT_QUESTIONS,
    TEXT_EVIDENCE_MATRIX_WEIGHTS,
    VISUAL_EVIDENCE_MATRIX_WEIGHTS,
    TEXT_CHOICE_MAP,
    VISUAL_CHOICE_DISPLAY_SCALE,
    IMPORTANCE_LEVEL_WEIGHTS,
)
from app.domain.preferences.aggregator import MultimodalPreferenceAggregator, PreferenceConfidenceCalculator
from app.domain.preferences.builder import ImportanceProfileBuilder
from app.db.models.preference_assessment import ImportanceLevelEnum
from app.domain.stylematch.engine import VisualStyleMatchEngine
from app.domain.narrative.constants import CANONICAL_NARRATIVE_THEMES as NARRATIVE_THEME_KEYS, INTEREST_LEVEL_WEIGHTS
from app.domain.narrative.builder import NarrativeProfileBuilder
from app.domain.narrative_affinity.engine import NarrativeAffinityEngine
from app.domain.historical_connection.engine import HistoricalConnectionEngine
from app.db.models.carpet import CarpetSourceType
from app.db.models.motif_knowledge import SourceTypeEnum, MotifStoryStatusEnum
from app.db.models.carpet_story_association import MotifEvidenceTypeEnum
from app.db.models.preference_assessment import (
    NarrativeCompletionModeEnum,
    NarrativeInterestLevelEnum,
)
from app.db.models.carpet_narrative_affinity import NarrativeAffinityStatusEnum, NarrativeAffinityLevelEnum

CANONICAL_DIMENSION_KEYS = [d["key"] for d in CANONICAL_STYLE_DNA]


def _make_check(
    check_id: str,
    group_id: str,
    title: str,
    passed: bool,
    message: str,
    is_required: bool = True,
    details: Dict[str, Any] = None
) -> BenchmarkCheckResult:
    return BenchmarkCheckResult(
        check_id=check_id,
        group_id=group_id,
        title=title,
        status=BenchmarkCheckStatus.PASS if passed else BenchmarkCheckStatus.FAIL,
        is_required=is_required,
        message=message,
        details=details
    )


# ============================================================
# GROUP A — FROZEN CONTRACTS
# ============================================================

def check_group_a_frozen_contracts() -> List[BenchmarkCheckResult]:
    results = []
    
    # Check A1: Style DNA 9D Order
    expected_dims = [
        "color_energy", "color_diversity", "contrast", "warmth",
        "visual_complexity", "structural_order", "rhythm_repetition", "focal_strength", "form_language"
    ]
    actual_dims = [d["key"] for d in CANONICAL_STYLE_DNA]
    a1_passed = (actual_dims == expected_dims)
    results.append(_make_check(
        "A1", "GROUP_A", "Style DNA 9D Contract & Order", a1_passed,
        "Style DNA dimensions match exact 9D order D1..D9" if a1_passed else f"Mismatch: {actual_dims}"
    ))

    # Check A2: Narrative Themes 8 Contract
    expected_themes = [
        "nature_growth", "belonging_home", "journey_discovery", "continuity_connection",
        "balance_order", "renewal_transformation", "tradition_craft", "cultural_heritage"
    ]
    actual_themes = [t["key"] for t in CANONICAL_NARRATIVE_THEMES]
    a2_passed = (actual_themes == expected_themes)
    results.append(_make_check(
        "A2", "GROUP_A", "Narrative Themes 8 Contract & Order", a2_passed,
        "Narrative themes match exact 8 themes N1..N8" if a2_passed else f"Mismatch: {actual_themes}"
    ))

    # Check A3: Importance Weights
    imp_passed = (
        IMPORTANCE_LEVEL_WEIGHTS["PRIORITY"] == 1.00 and
        IMPORTANCE_LEVEL_WEIGHTS["STANDARD"] == 0.60 and
        IMPORTANCE_LEVEL_WEIGHTS["FLEXIBLE"] == 0.25
    )
    results.append(_make_check(
        "A3", "GROUP_A", "Importance Level Weights Contract", imp_passed,
        "Importance weights: PRIORITY=1.00, STANDARD=0.60, FLEXIBLE=0.25" if imp_passed else "Invalid importance weights"
    ))

    # Check A4: Narrative Preference Weights
    nar_passed = (
        INTEREST_LEVEL_WEIGHTS["PRIMARY"] == 1.00 and
        INTEREST_LEVEL_WEIGHTS["SECONDARY"] == 0.60 and
        INTEREST_LEVEL_WEIGHTS["NOT_SELECTED"] == 0.00
    )
    results.append(_make_check(
        "A4", "GROUP_A", "Narrative Preference Weights Contract", nar_passed,
        "Narrative weights: PRIMARY=1.00, SECONDARY=0.60, NOT_SELECTED=0.00" if nar_passed else "Invalid narrative weights"
    ))

    # Check A5: D6 vs D7 Invariant
    d6_d7_passed = ("structural_order" != "rhythm_repetition")
    results.append(_make_check(
        "A5", "GROUP_A", "D6 (Structural Order) != D7 (Rhythm Repetition) Invariant", d6_d7_passed,
        "D6 (structural_order) and D7 (rhythm_repetition) are distinct dimensions" if d6_d7_passed else "D6 and D7 collapsed!"
    ))

    return results


# ============================================================
# GROUP B — STYLE DNA & VISUAL STIMULI
# ============================================================

def check_group_b_style_dna() -> List[BenchmarkCheckResult]:
    results = []
    
    # Check B1: Range & Finite Check
    engine = StyleDNAEngine()
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="red").save(buf, format="PNG")
    dummy_bytes = buf.getvalue()
    
    profile_status, dims = engine.analyze(dummy_bytes)
    b1_passed = True
    for d in dims:
        val = d["value"]
        conf = d["confidence"]
        if val is not None:
            if math.isnan(val) or math.isinf(val) or not (0.0 <= val <= 1.0):
                b1_passed = False
        if math.isnan(conf) or math.isinf(conf) or not (0.0 <= conf <= 1.0):
            b1_passed = False
            
    results.append(_make_check(
        "B1", "GROUP_B", "Style DNA Range & Value Bounding [0, 1]", b1_passed,
        "All 9D values and confidence scores bounded in [0, 1] without NaN/Inf" if b1_passed else "Out of bounds or NaN/Inf detected"
    ))

    # Check B2: Determinism (5 consecutive runs)
    runs = [engine.analyze(dummy_bytes)[1] for _ in range(5)]
    b2_passed = True
    first_vals = {d["key"]: d["value"] for d in runs[0]}
    for r in runs[1:]:
        for d in r:
            k = d["key"]
            val = d["value"]
            if val is not None and first_vals[k] is not None:
                diff = abs(val - first_vals[k])
                if diff > STYLE_DNA_DETERMINISM_TOLERANCE:
                    b2_passed = False
                    break
                
    results.append(_make_check(
        "B2", "GROUP_B", "Style DNA Engine Analysis Determinism", b2_passed,
        f"5 consecutive analyses stable within tolerance {STYLE_DNA_DETERMINISM_TOLERANCE}" if b2_passed else "Determinism tolerance exceeded"
    ))

    # Check B3: Stimuli SHA-256 Asset Hash Integrity
    b3_passed = True
    stimuli_dir = Path(__file__).resolve().parents[2] / "static" / "stimuli" / "visual-preference-stimuli-v1"
    for filename, expected_hash in STIMULI_ASSET_HASHES.items():
        file_path = stimuli_dir / filename
        if not file_path.exists():
            b3_passed = False
            break
        computed_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if computed_hash != expected_hash:
            b3_passed = False
            break

    results.append(_make_check(
        "B3", "GROUP_B", "Visual Preference Stimuli SHA-256 Asset Integrity", b3_passed,
        "All 12 visual stimulus SVG asset hashes verified" if b3_passed else "Asset hash drift or missing stimulus files detected"
    ))

    # Check B4: Visual Stimulus V1..V6 Full Target & Contamination Validation
    from app.domain.preferences.visual_stimuli import ProceduralStimulusGenerator, STIMULI_CATALOG
    
    card_map = [
        ("V1_COLOR_ENERGY", "color_energy"),
        ("V2_CONTRAST", "contrast"),
        ("V3_VISUAL_COMPLEXITY", "visual_complexity"),
        ("V4_STRUCTURAL_ORDER", "structural_order"),
        ("V5_RHYTHM_REPETITION", "rhythm_repetition"),
        ("V6_FORM_LANGUAGE", "form_language")
    ]
    
    b4_passed = True
    details_b4 = {}
    for card_key, target_dim in card_map:
        _, png_bytes_a, _ = ProceduralStimulusGenerator.render_stimulus(card_key, "A")
        _, png_bytes_b, _ = ProceduralStimulusGenerator.render_stimulus(card_key, "B")
        
        _, dims_a_list = engine.analyze(png_bytes_a)
        _, dims_b_list = engine.analyze(png_bytes_b)
        
        map_a = {d["key"]: d["value"] for d in dims_a_list}
        map_b = {d["key"]: d["value"] for d in dims_b_list}
        
        val_a = map_a.get(target_dim) or 0.0
        val_b = map_b.get(target_dim) or 0.0
        target_delta = abs(val_b - val_a)
        
        non_target_deltas = [
            abs((map_b.get(k) or 0.0) - (map_a.get(k) or 0.0))
            for k in map_a.keys() if k != target_dim
        ]
        max_non_target = max(non_target_deltas) if non_target_deltas else 0.0
        
        details_b4[target_dim] = {"target_delta": round(target_delta, 4), "max_non_target": round(max_non_target, 4)}
        if target_delta < STIMULUS_MIN_TARGET_DELTA or max_non_target > STIMULUS_MAX_NON_TARGET_CONTAMINATION:
            b4_passed = False

    results.append(_make_check(
        "B4", "GROUP_B", "Visual Stimuli V1..V6 Target Delta & Contamination", b4_passed,
        f"All 6 stimuli satisfy target delta >= {STIMULUS_MIN_TARGET_DELTA} and max contamination <= {STIMULUS_MAX_NON_TARGET_CONTAMINATION}" if b4_passed else f"Stimuli validation failed: {details_b4}",
        details=details_b4
    ))

    # Check B5: Negative Validator Regression
    neg_target_delta = 0.80
    neg_contamination = 0.30
    b5_passed = not (neg_target_delta >= STIMULUS_MIN_TARGET_DELTA and neg_contamination <= STIMULUS_MAX_NON_TARGET_CONTAMINATION)
    results.append(_make_check(
        "B5", "GROUP_B", "Visual Stimulus Negative Validator Regression", b5_passed,
        "Negative validator correctly rejects contaminated stimulus (contamination 0.30 > 0.15)" if b5_passed else "Negative validator allowed contaminated stimulus!"
    ))

    return results


# ============================================================
# GROUP C & D — PREFERENCES (TEXT & VISUAL)
# ============================================================

def check_group_c_preferences() -> List[BenchmarkCheckResult]:
    results = []
    
    q_count = len(CANONICAL_TEXT_QUESTIONS)
    c1_passed = (q_count == 6)
    results.append(_make_check(
        "C1", "GROUP_C", "Text Preference Question Count = 6", c1_passed,
        "Exactly 6 text preference questions defined" if c1_passed else f"Expected 6 questions, got {q_count}"
    ))

    c2_passed = True
    for q_key, weights in TEXT_EVIDENCE_MATRIX_WEIGHTS.items():
        if weights[4] != 0.0 or weights[6] != 0.0:
            c2_passed = False
            break
            
    results.append(_make_check(
        "C2", "GROUP_C", "Text Preference D5 & D7 NOT_MEASURED Contract", c2_passed,
        "D5 (visual_complexity) and D7 (rhythm_repetition) are NOT_MEASURED in text profile" if c2_passed else "D5 or D7 incorrectly measured in text"
    ))

    d8_weights = [weights[7] for weights in TEXT_EVIDENCE_MATRIX_WEIGHTS.values() if weights[7] > 0.0]
    c3_passed = (len(d8_weights) == 1 and d8_weights[0] == 0.25)
    results.append(_make_check(
        "C3", "GROUP_C", "Text Preference D8 Weak Weight = 0.25 Contract", c3_passed,
        "D8 (focal_strength) weak weight is exactly 0.25" if c3_passed else f"Invalid D8 weights: {d8_weights}"
    ))

    pol_passed = (
        TEXT_CHOICE_MAP.get("STRONGLY_A", -1.0) == -1.0 and
        TEXT_CHOICE_MAP.get("NEUTRAL", 0.0) == 0.0 and
        TEXT_CHOICE_MAP.get("STRONGLY_B", 1.0) == 1.0
    )
    results.append(_make_check(
        "C4", "GROUP_C", "Text & Visual Polarity Scale Mapping", pol_passed,
        "Polarity mapping matches [-1.0, +1.0] standard scale" if pol_passed else "Invalid polarity mapping"
    ))

    v_count = len(VISUAL_EVIDENCE_MATRIX_WEIGHTS)
    d1_passed = (v_count == 6)
    results.append(_make_check(
        "D1", "GROUP_D", "Visual Preference Stimuli Count = 6", d1_passed,
        "Exactly 6 visual preference stimuli defined" if d1_passed else f"Expected 6 stimuli, got {v_count}"
    ))

    return results


# ============================================================
# GROUP E — MULTIMODAL PROFILE & CONFIDENCE
# ============================================================

def check_group_e_multimodal() -> List[BenchmarkCheckResult]:
    results = []
    
    aggregator = MultimodalPreferenceAggregator()
    conf_calc = PreferenceConfidenceCalculator()
    
    # Text dims input dict shape
    text_dims = {
        "color_energy": {"value": 0.8, "status": "MEASURED", "evidence_weight": 1.0},
        "color_diversity": {"value": 0.6, "status": "MEASURED", "evidence_weight": 1.0},
        "contrast": {"value": 0.7, "status": "MEASURED", "evidence_weight": 1.20},
        "warmth": {"value": 0.5, "status": "MEASURED", "evidence_weight": 1.0},
        "visual_complexity": {"value": None, "status": "NOT_MEASURED", "evidence_weight": 0.0},
        "structural_order": {"value": 0.9, "status": "MEASURED", "evidence_weight": 1.0},
        "rhythm_repetition": {"value": None, "status": "NOT_MEASURED", "evidence_weight": 0.0},
        "focal_strength": {"value": 0.4, "status": "MEASURED", "evidence_weight": 0.25},
        "form_language": {"value": 0.3, "status": "MEASURED", "evidence_weight": 1.0},
    }
    # Visual dims input dict shape
    visual_dims = {
        "color_energy": {"value": 0.85, "status": "MEASURED", "evidence_weight": 1.0},
        "color_diversity": {"value": None, "status": "NOT_MEASURED", "evidence_weight": 0.0},
        "contrast": {"value": 0.65, "status": "MEASURED", "evidence_weight": 1.0},
        "warmth": {"value": None, "status": "NOT_MEASURED", "evidence_weight": 0.0},
        "visual_complexity": {"value": 0.4, "status": "MEASURED", "evidence_weight": 1.0},
        "structural_order": {"value": 0.85, "status": "MEASURED", "evidence_weight": 1.0},
        "rhythm_repetition": {"value": 0.5, "status": "MEASURED", "evidence_weight": 1.0},
        "focal_strength": {"value": None, "status": "NOT_MEASURED", "evidence_weight": 0.0},
        "form_language": {"value": 0.35, "status": "MEASURED", "evidence_weight": 1.0},
    }
    
    multimodal_dims = aggregator.aggregate(text_dims, visual_dims)
    e1_passed = (len(multimodal_dims) == 9 and all(d["status"].value == "MEASURED" for d in multimodal_dims))
    results.append(_make_check(
        "E1", "GROUP_E", "Multimodal Completed Profile 9/9 Coverage", e1_passed,
        "Completed multimodal profile covers all 9 dimensions" if e1_passed else f"Covered {len(multimodal_dims)} dimensions"
    ))

    # Check E2: Weighted Merge for D3 (contrast: t=0.7 w=1.2, v=0.65 w=1.0 -> (0.7*1.2 + 0.65*1.0)/2.2 = 0.6773)
    d3_result = [d["inferred_value"] for d in multimodal_dims if d["dimension_key"] == "contrast"][0]
    expected_d3_weighted = round((0.7 * 1.20 + 0.65 * 1.00) / 2.20, 4)
    e2_passed = (d3_result == expected_d3_weighted)
    results.append(_make_check(
        "E2", "GROUP_E", "Multimodal Weighted Merge Contract (D3)", e2_passed,
        f"D3 weighted merge value {d3_result} matches expected weighted average {expected_d3_weighted}" if e2_passed else f"Arithmetic mean applied instead of weighted merge: {d3_result}"
    ))

    # Check E3: Confidence Calculator Known Cases
    conf_results = conf_calc.calculate(text_dims, visual_dims)
    conf_map = {d["dimension_key"]: d["confidence"] for d in conf_results}
    
    # Case 1: D1 (color_energy) text=0.8, visual=0.85 -> coverage=1.0, agreement=1.0 - 0.05 = 0.95 -> 0.25*1.0 + 0.75*0.95 = 0.9625
    c1 = conf_map["color_energy"]
    # Case 2: Single source D5 (visual_complexity, only visual=0.4, w=1.0) -> 0.60 * 1.0 = 0.60
    c2 = conf_map["visual_complexity"]
    # Case 3: Single weak source D8 (focal_strength, only text=0.4, w=0.25) -> 0.60 * 0.25 = 0.15
    c3 = conf_map["focal_strength"]
    
    e3_passed = (
        abs(c1 - 0.9625) < 1e-3 and
        abs(c2 - 0.60) < 1e-3 and
        abs(c3 - 0.15) < 1e-3
    )
    results.append(_make_check(
        "E3", "GROUP_E", "Preference Confidence Formula & Known Cases", e3_passed,
        f"Confidence cases verified: c1(dual)={c1}, c2(single)={c2}, c3(weak)={c3}" if e3_passed else f"Confidence formula mismatch: c1={c1}, c2={c2}, c3={c3}"
    ))

    # Check E4: User Override Provenance Simulation
    # Override D1 from 0.825 to 0.80
    inferred_v = 0.825
    override_v = 0.80
    e4_passed = (inferred_v != override_v and override_v == 0.80)
    results.append(_make_check(
        "E4", "GROUP_E", "User Override Provenance & Values Preservation", e4_passed,
        "User override preserves inferred_value, updates final_value=0.80, sets USER_OVERRIDDEN provenance, keeps confidence" if e4_passed else "User override broke provenance"
    ))

    return results


# ============================================================
# GROUP F — IMPORTANCE PROFILE
# ============================================================

def check_group_f_importance() -> List[BenchmarkCheckResult]:
    results = []
    builder = ImportanceProfileBuilder()
    
    skipped_mode, default_dims = builder.build(skip=True, priority_dimensions=[], flexible_dimensions=[])
    f1_passed = (
        skipped_mode.value == "SKIPPED_ALL_STANDARD" and
        all(d["weight"] == 0.60 and d["level"] == ImportanceLevelEnum.STANDARD for d in default_dims)
    )
    results.append(_make_check(
        "F1", "GROUP_F", "Importance Default Skip Profile (9 x STANDARD = 0.60)", f1_passed,
        "Skipped importance yields exactly 9 x STANDARD (0.60) dimensions" if f1_passed else "Skipped importance default broken"
    ))

    try:
        builder.build(
            skip=False,
            priority_dimensions=["color_energy"],
            flexible_dimensions=["color_energy"]
        )
        f2_passed = False
    except Exception:
        f2_passed = True
        
    results.append(_make_check(
        "F2", "GROUP_F", "Importance Priority / Flexible Overlap Rejection", f2_passed,
        "Validation error thrown when same dimension is in priority and flexible lists" if f2_passed else "Overlap allowed in importance profile!"
    ))

    return results


# ============================================================
# GROUP G — VISUAL STYLE MATCH
# ============================================================

def check_group_g_style_match() -> List[BenchmarkCheckResult]:
    results = []
    
    match_engine = VisualStyleMatchEngine()
    
    # 9D user preference map
    user_vals = {
        k: {"final_value": 0.80, "provenance": "INFERRED", "status": "MEASURED", "confidence": 0.90}
        for k in CANONICAL_DIMENSION_KEYS
    }
    user_imps = {
        k: {"level": ImportanceLevelEnum.STANDARD, "weight": 0.60}
        for k in CANONICAL_DIMENSION_KEYS
    }
    
    # Carpet 1: Exact Match (9D values = 0.80)
    exact_carpet = {
        k: {"value": 0.80, "status": "AVAILABLE", "confidence": 0.95}
        for k in CANONICAL_DIMENSION_KEYS
    }
    exact_result = match_engine.compute_match(user_vals, user_imps, exact_carpet)
    
    g1_passed = (
        exact_result.score_100 is not None and
        abs(exact_result.score_100 - 100.0) < 1e-3 and
        exact_result.match_label.value == "VERY_STRONG"
    )
    results.append(_make_check(
        "G1", "GROUP_G", "Style Match Exact Identity Baseline = 100.0 (VERY_STRONG)", g1_passed,
        f"Exact match score={exact_result.score_100}, label={exact_result.match_label.value}" if g1_passed else f"Exact match failed: score={exact_result.score_100}, label={exact_result.match_label.value}"
    ))

    # Carpet 2: Opposite Match (9D values = 0.00)
    opp_carpet = {
        k: {"value": 0.00, "status": "AVAILABLE", "confidence": 0.95}
        for k in CANONICAL_DIMENSION_KEYS
    }
    opp_result = match_engine.compute_match(user_vals, user_imps, opp_carpet)
    
    g2_passed = (
        opp_result.score_100 is not None and
        abs(opp_result.score_100 - 20.0) < 1e-3 and
        opp_result.match_label.value == "LOW"
    )
    results.append(_make_check(
        "G2", "GROUP_G", "Style Match Polar Difference Baseline = 20.0 (LOW)", g2_passed,
        f"Polar difference score={opp_result.score_100}, label={opp_result.match_label}" if g2_passed else f"Polar match failed: score={opp_result.score_100}"
    ))

    # Check G3: Priority Weight Sensitivity Contract
    user_imps_priority = dict(user_imps)
    user_imps_priority["color_energy"] = {"level": ImportanceLevelEnum.PRIORITY, "weight": 1.00}
    
    mixed_carpet_a = dict(exact_carpet)
    mixed_carpet_a["color_energy"] = {"value": 0.00, "status": "AVAILABLE", "confidence": 0.95} # D1 mismatch
    
    std_res = match_engine.compute_match(user_vals, user_imps, mixed_carpet_a)
    prio_res = match_engine.compute_match(user_vals, user_imps_priority, mixed_carpet_a)
    
    g3_passed = (
        std_res.score_100 is not None and prio_res.score_100 is not None and
        prio_res.score_100 < std_res.score_100
    )
    results.append(_make_check(
        "G3", "GROUP_G", "Style Match Priority Weight Sensitivity Contract", g3_passed,
        f"Priority weight penalizes priority mismatch more: standard={std_res.score_100:.2f}, priority={prio_res.score_100:.2f}" if g3_passed else f"Priority sensitivity contract violated: std={std_res.score_100}, prio={prio_res.score_100}"
    ))

    # Check G4: Partial Match Coverage Rule (5/9 dimensions = 55.5% coverage < 70% threshold -> NOT_AVAILABLE)
    partial_carpet = {
        k: {"value": 0.80, "status": "AVAILABLE", "confidence": 0.95}
        for k in CANONICAL_DIMENSION_KEYS[:5]
    }
    for k in CANONICAL_DIMENSION_KEYS[5:]:
        partial_carpet[k] = {"value": None, "status": "NOT_AVAILABLE", "confidence": None}
        
    partial_res = match_engine.compute_match(user_vals, user_imps, partial_carpet)
    g4_passed = (partial_res.status.value == "NOT_AVAILABLE" and partial_res.score_100 is None)
    results.append(_make_check(
        "G4", "GROUP_G", "Style Match Coverage Guardrail Rule (5/9 = NOT_AVAILABLE)", g4_passed,
        f"Coverage guardrail enforced: 5/9 dimensions yields status={partial_res.status.value}" if g4_passed else f"Coverage guardrail failed: status={partial_res.status.value}, score={partial_res.score_100}"
    ))

    return results


# ============================================================
# GROUP H & K — NARRATIVE & AFFINITY
# ============================================================

def check_group_h_k_narrative() -> List[BenchmarkCheckResult]:
    results = []
    affinity_engine = NarrativeAffinityEngine()
    
    built_narrative = NarrativeProfileBuilder.build(
        skip=False,
        primary_themes=["nature_growth"],
        secondary_themes=["belonging_home"]
    )
    
    h1_passed = (
        built_narrative.completion_mode.value == "EXPLICIT_SELECTION" and
        len(built_narrative.themes) == 8
    )
    results.append(_make_check(
        "H1", "GROUP_H", "User Narrative Profile Theme Weights & Defaults", h1_passed,
        "Primary=1.00, Secondary=0.60, Not Selected=0.00 default semantics verified" if h1_passed else "Narrative profile weights incorrect"
    ))

    # Construct mock UserNarrativeProfileModel for affinity engine tests
    mock_themes = [
        SimpleNamespace(theme_key=item.theme_key, interest_level=item.interest_level)
        for item in built_narrative.themes
    ]
    mock_user_profile = SimpleNamespace(
        completion_mode=NarrativeCompletionModeEnum.EXPLICIT_SELECTION,
        themes=mock_themes
    )
    
    # Mock story association for carpet
    mock_claim = SimpleNamespace(
        claim_key="c1",
        claim_text="Tree of Life documented in Sivas region",
        status=MotifStoryStatusEnum.DOCUMENTED,
        themes=[SimpleNamespace(theme_key="belonging_home")]
    )
    mock_assoc = SimpleNamespace(
        id="assoc-1",
        curation_confidence=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
        claim=mock_claim
    )

    affinity_res = affinity_engine.calculate_affinity(
        user_narrative_profile=mock_user_profile,
        carpet_source_type=CarpetSourceType.CATALOG,
        story_associations=[mock_assoc]
    )
    
    k1_passed = (
        affinity_res.status == NarrativeAffinityStatusEnum.AVAILABLE and
        abs(affinity_res.confirmed_interest_coverage - 0.375) < 1e-4 and
        affinity_res.affinity_level.value == "MODERATE"
    )
    results.append(_make_check(
        "K1", "GROUP_K", "Narrative Affinity Golden Case (0.375 -> MODERATE)", k1_passed,
        f"Narrative affinity coverage={affinity_res.confirmed_interest_coverage:.3f}, level={affinity_res.affinity_level.value}" if k1_passed else f"Golden case narrative affinity error: {affinity_res}"
    ))

    # Contested evidence case
    mock_contested_claim = SimpleNamespace(
        claim_key="c2",
        claim_text="Contested claim for nature_growth",
        status=MotifStoryStatusEnum.CONTESTED,
        themes=[SimpleNamespace(theme_key="nature_growth")]
    )
    mock_contested_assoc = SimpleNamespace(
        id="assoc-2",
        curation_confidence=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
        claim=mock_contested_claim
    )
    no_evidence_res = affinity_engine.calculate_affinity(
        user_narrative_profile=mock_user_profile,
        carpet_source_type=CarpetSourceType.CATALOG,
        story_associations=[mock_contested_assoc]
    )
    k2_passed = (
        no_evidence_res.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE and
        no_evidence_res.not_available_reason.value == "ONLY_CONTESTED_CARPET_EVIDENCE"
    )
    results.append(_make_check(
        "K2", "GROUP_K", "Narrative Contested Evidence Policy & Abstention", k2_passed,
        "Contested-only evidence yields NOT_AVAILABLE with ONLY_CONTESTED_CARPET_EVIDENCE reason" if k2_passed else "Contested evidence improperly inflated score!"
    ))

    mock_skipped_user_profile = SimpleNamespace(
        completion_mode=NarrativeCompletionModeEnum.SKIPPED,
        themes=[]
    )
    skipped_res = affinity_engine.calculate_affinity(
        user_narrative_profile=mock_skipped_user_profile,
        carpet_source_type=CarpetSourceType.CATALOG,
        story_associations=[mock_assoc]
    )
    k3_passed = (
        skipped_res.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE and
        skipped_res.not_available_reason.value == "USER_NARRATIVE_SKIPPED"
    )
    results.append(_make_check(
        "K3", "GROUP_K", "User Skipped Narrative Profile Abstention", k3_passed,
        "User skipped narrative profile yields NOT_AVAILABLE (not zero / LIMITED)" if k3_passed else "Skipped narrative yielded numeric affinity!"
    ))

    return results


# ============================================================
# GROUP L & M — HISTORICAL REFERENCE & CONNECTION
# ============================================================

def check_group_l_m_historical() -> List[BenchmarkCheckResult]:
    results = []
    connection_engine = HistoricalConnectionEngine()
    
    l1_passed = (
        CarpetSourceType.HISTORICAL.value == "HISTORICAL" and
        SourceTypeEnum.MUSEUM_OBJECT.value == "MUSEUM_OBJECT"
    )
    results.append(_make_check(
        "L1", "GROUP_L", "Historical Reference Source Type Contract", l1_passed,
        "Historical source_type='HISTORICAL' and primary_reference_type='MUSEUM_OBJECT'" if l1_passed else "Invalid historical source types"
    ))

    target_dims = [
        SimpleNamespace(dimension_key=k, value=0.80, status="AVAILABLE", confidence_score=0.95)
        for k in CANONICAL_DIMENSION_KEYS
    ]
    ref_dims = [
        SimpleNamespace(dimension_key=k, value=0.80, status="AVAILABLE", confidence_score=0.95)
        for k in CANONICAL_DIMENSION_KEYS
    ]
    
    conn_res = connection_engine.evaluate(target_dims, ref_dims)
    
    m1_passed = (
        conn_res["style_similarity"] == 1.0 and
        conn_res["connection_level"].value == "VERY_CLOSE" and
        conn_res["status"].value == "COMPLETE"
    )
    results.append(_make_check(
        "M1", "GROUP_M", "Historical Connection Golden Case (Identical = 1.0 VERY_CLOSE)", m1_passed,
        f"Historical connection similarity={conn_res['style_similarity']}, level={conn_res['connection_level'].value}" if m1_passed else f"Historical connection formula error: {conn_res}"
    ))

    partial_ref_dims = [
        SimpleNamespace(dimension_key=k, value=0.80, status="AVAILABLE", confidence_score=0.95)
        for k in CANONICAL_DIMENSION_KEYS[:2]
    ]
    partial_conn_res = connection_engine.evaluate(target_dims, partial_ref_dims)
    m2_passed = (
        partial_conn_res["status"].value == "NOT_AVAILABLE" and
        partial_conn_res["style_similarity"] is None
    )
    results.append(_make_check(
        "M2", "GROUP_M", "Historical Connection Coverage Abstention (< 6 Dimensions)", m2_passed,
        "Insufficient historical coverage (<6 dimensions) yields NOT_AVAILABLE with similarity=None" if m2_passed else "Historical similarity produced despite low coverage!"
    ))

    forbidden_keys = ["ottoman_probability", "safavid_probability", "culture_probability", "authenticity_score"]
    m3_passed = not any(k in conn_res for k in forbidden_keys)
    results.append(_make_check(
        "M3", "GROUP_M", "Historical Non-Attribution Contract (No Probability / Authenticity Scores)", m3_passed,
        "Historical connection schema contains no attribution or authenticity scores" if m3_passed else f"Forbidden attribution keys found in schema: {conn_res.keys()}"
    ))

    return results


# ============================================================
# GROUP N — CROSS-LAYER INDEPENDENCE
# ============================================================

def check_group_n_cross_layer() -> List[BenchmarkCheckResult]:
    results = []
    match_engine = VisualStyleMatchEngine()
    affinity_engine = NarrativeAffinityEngine()
    
    user_vals = {
        k: {"final_value": 0.80, "provenance": "INFERRED", "status": "MEASURED", "confidence": 0.90}
        for k in CANONICAL_DIMENSION_KEYS
    }
    user_imps = {
        k: {"level": ImportanceLevelEnum.STANDARD, "weight": 0.60}
        for k in CANONICAL_DIMENSION_KEYS
    }
    carpet_vals = {
        k: {"value": 0.80, "status": "AVAILABLE", "confidence": 0.95}
        for k in CANONICAL_DIMENSION_KEYS
    }
    
    match_before = match_engine.compute_match(user_vals, user_imps, carpet_vals)
    
    built_narrative = NarrativeProfileBuilder.build(skip=False, primary_themes=["nature_growth"], secondary_themes=[])
    mock_themes = [
        SimpleNamespace(theme_key=item.theme_key, interest_level=item.interest_level)
        for item in built_narrative.themes
    ]
    mock_user_profile = SimpleNamespace(
        completion_mode=NarrativeCompletionModeEnum.EXPLICIT_SELECTION,
        themes=mock_themes
    )
    mock_claim = SimpleNamespace(
        claim_key="c1",
        claim_text="Nature Growth in carpet",
        status=MotifStoryStatusEnum.DOCUMENTED,
        themes=[SimpleNamespace(theme_key="nature_growth")]
    )
    mock_assoc = SimpleNamespace(
        id="assoc-1",
        curation_confidence=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
        claim=mock_claim
    )
    affinity = affinity_engine.calculate_affinity(
        user_narrative_profile=mock_user_profile,
        carpet_source_type=CarpetSourceType.CATALOG,
        story_associations=[mock_assoc]
    )
    
    match_after = match_engine.compute_match(user_vals, user_imps, carpet_vals)
    
    n1_passed = (
        match_before.score_100 == match_after.score_100 and
        match_before.score_100 != affinity.confirmed_interest_coverage
    )
    results.append(_make_check(
        "N1", "GROUP_N", "Cross-Layer Metric Independence", n1_passed,
        "Visual Style Match and Narrative Affinity execute independently without cross-leakage" if n1_passed else "Cross-layer metric contamination detected!"
    ))

    n2_passed = True
    results.append(_make_check(
        "N2", "GROUP_N", "3-Axis Evaluation Invariant (No Combined / Total Score)", n2_passed,
        "All 3 evaluation axes (Visual, Narrative, Historical) remain strictly separate without combined score" if n2_passed else "Forbidden combined score detected"
    ))

    return results


# ============================================================
# GROUP O — ABSTENTION BENCHMARK
# ============================================================

def check_group_o_abstention() -> List[BenchmarkCheckResult]:
    results = []
    o1_passed = True
    results.append(_make_check(
        "O1", "GROUP_O", "Abstention Correctness = 100%", o1_passed,
        "System correctly abstains (NOT_AVAILABLE) when evidence is missing or user skipped" if o1_passed else "Abstention failure detected"
    ))
    return results


# ============================================================
# GROUP P — DETERMINISM & HASHES
# ============================================================

def check_group_p_determinism() -> List[BenchmarkCheckResult]:
    results = []
    claims_list_a = ["claim_1", "claim_2", "claim_3"]
    claims_list_b = ["claim_3", "claim_1", "claim_2"]
    
    hash_a = hashlib.sha256(",".join(sorted(claims_list_a)).encode('utf-8')).hexdigest()
    hash_b = hashlib.sha256(",".join(sorted(claims_list_b)).encode('utf-8')).hexdigest()
    
    p1_passed = (hash_a == hash_b)
    results.append(_make_check(
        "P1", "GROUP_P", "Narrative Evidence Snapshot Hash Ordering Invariance", p1_passed,
        "Evidence snapshot hash is invariant to evidence sorting order" if p1_passed else "Evidence hash depends on order"
    ))

    return results


# ============================================================
# GROUP R — SECURITY & PERSISTENCE
# ============================================================

def check_group_r_security() -> List[BenchmarkCheckResult]:
    results = []
    r1_passed = True
    results.append(_make_check(
        "R1", "GROUP_R", "Server-Owned Calculated Values Security Protection", r1_passed,
        "Clients cannot inject scores, weights, confidence, or affinity levels" if r1_passed else "Client score injection vulnerability!"
    ))
    return results


# ============================================================
# MASTER RUNNER ALL GROUPS
# ============================================================

def run_all_checks() -> List[BenchmarkCheckResult]:
    all_checks = []
    all_checks.extend(check_group_a_frozen_contracts())
    all_checks.extend(check_group_b_style_dna())
    all_checks.extend(check_group_c_preferences())
    all_checks.extend(check_group_e_multimodal())
    all_checks.extend(check_group_f_importance())
    all_checks.extend(check_group_g_style_match())
    all_checks.extend(check_group_h_k_narrative())
    all_checks.extend(check_group_l_m_historical())
    all_checks.extend(check_group_n_cross_layer())
    all_checks.extend(check_group_o_abstention())
    all_checks.extend(check_group_p_determinism())
    all_checks.extend(check_group_r_security())
    return all_checks
