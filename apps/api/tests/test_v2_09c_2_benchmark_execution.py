"""
V2-09C.2 Benchmark Execution Integration and Artifact Verification Tests.

Verifies:
1. Benchmark result artifact small-vlm-benchmark-result-v1.json exists and contains PASS_BENCHMARK_COMPLETE.
2. Candidate evaluations for C1, C2, C3 are present, and R0 is properly recorded as NOT_EVALUATED_RUNTIME_EXCLUDED.
3. First-look audit record real-test-first-look-audit.json exists with pre_run_freeze_verification = PASS and timestamp.
4. Benchmark case counts (286 total cases per candidate: 128 synthetic, 109 real GT, 12 detect proposals, 37 obb proposals).
5. Exact VLM call count on REAL_TEST (474 total calls across eligible candidates C1, C2, C3).
6. Immutable frozen hash alignment across prompt, schema, compositor, generation policy, and 17-key registry.
"""

import json
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
BENCHMARK_RESULT_PATH = ROOT_DIR / "data/validation/v2-09c/small-vlm-benchmark-result-v1.json"
FIRST_LOOK_AUDIT_PATH = ROOT_DIR / "data/validation/v2-09c/real-test-first-look-audit.json"
BENCHMARK_FREEZE_PATH = ROOT_DIR / "data/validation/v2-09c/visual-verifier-benchmark-freeze.json"
MANIFESTS_PATH = ROOT_DIR / "data/validation/v2-09c/benchmark-case-manifests.json"


def test_v2_09c_2_result_artifact_exists_and_valid():
    assert BENCHMARK_RESULT_PATH.exists(), f"Missing benchmark result artifact at {BENCHMARK_RESULT_PATH}"
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    
    assert data["task"] == "V2-09C.2 — Frozen Small-VLM Visual Verifier Benchmark Execution"
    assert data["status"] == "PASS_BENCHMARK_COMPLETE"
    assert "benchmark_run_id" in data
    assert "generated_at" in data


def test_v2_09c_2_contract_hashes_match_freeze():
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    contract = data["contract"]
    
    assert contract["verifier_version"] == "visual-verifier-v1.0.0"
    assert contract["prompt_template_version"] == "motif-visual-verifier-prompt-v1.0.0"
    assert contract["prompt_template_sha256"] == "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"
    assert contract["schema_hash"] == "aa63efd246a867f84ba931900589343fc080f18f6dab2155552bac10d41547f8"
    assert contract["compositor_hash"] == "6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d"
    assert contract["generation_policy_sha256"] == "58edebf465f41a52c6a413fbf90ad1d84a08e2b980c132b4d07c015660f283a6"
    assert contract["proposal_threshold"] == 0.25
    assert contract["real_test_vlm_call_count"] == 474


def test_v2_09c_2_first_look_audit_artifact():
    assert FIRST_LOOK_AUDIT_PATH.exists(), f"Missing first look audit at {FIRST_LOOK_AUDIT_PATH}"
    audit = json.loads(FIRST_LOOK_AUDIT_PATH.read_text(encoding="utf-8"))
    
    assert audit["benchmark_phase"] == "V2-09C.2"
    assert audit["pre_run_freeze_verification"] == "PASS"
    assert audit["real_test_opened_at"] == "2026-08-18T08:18:27Z"
    assert audit["real_test_first_evaluated_model"] == "C1"
    assert audit["post_open_modifications"] == "NONE"
    
    timestamps = audit["candidate_first_look_timestamps"]
    assert "C1" in timestamps
    assert "C2" in timestamps
    assert "C3" in timestamps


def test_v2_09c_2_manifest_summary_and_cases():
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    m_summary = data["manifest_summary"]
    
    assert m_summary["synthetic_controlled_cases"] == 128
    assert m_summary["real_gt_controlled_cases"] == 109
    assert m_summary["real_detector_detect_cases"] == 12
    assert m_summary["real_detector_obb_cases"] == 37
    
    total_cases_per_candidate = (
        m_summary["synthetic_controlled_cases"]
        + m_summary["real_gt_controlled_cases"]
        + m_summary["real_detector_detect_cases"]
        + m_summary["real_detector_obb_cases"]
    )
    assert total_cases_per_candidate == 286


def test_v2_09c_2_candidate_evaluation_structures():
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    
    assert set(candidates.keys()) == {"C1", "C2", "C3", "R0"}
    
    # R0 exclusion check
    r0 = candidates["R0"]
    assert r0["status"] == "NOT_EVALUATED_RUNTIME_EXCLUDED"
    assert "AWQ INT4 compilation constraint" in r0["exclusion_reason"]
    
    # Eligible candidates (C1, C2, C3)
    for c_id in ["C1", "C2", "C3"]:
        cand = candidates[c_id]
        assert cand["candidate_id"] == c_id
        assert cand["raw_case_results_count"] == 286
        
        # Telemetry check
        assert "load_telemetry" in cand
        assert "resource_telemetry" in cand
        assert cand["resource_telemetry"]["wall_clock_seconds"] > 0
        assert cand["resource_telemetry"]["mean_latency_seconds"] > 0
        
        # Synthetic controlled layer check
        sc = cand["synthetic_controlled"]
        assert sc["total_cases"] == 128
        assert "schema_valid_rate" in sc
        assert "semantic_valid_rate" in sc
        assert "per_family_hard_negatives" in sc
        
        # Real GT controlled layer check
        rc = cand["real_gt_controlled"]
        assert rc["total_cases"] == 109
        
        # Detector pipeline checks
        dp = cand["detector_detect_pipeline"]
        assert dp["detector_baseline"]["proposals"] == 12
        assert dp["detector_baseline"]["tp"] == 1
        assert dp["detector_baseline"]["fp"] == 11
        assert dp["detector_baseline"]["fn"] == 91
        
        op = cand["detector_obb_pipeline"]
        assert op["detector_baseline"]["proposals"] == 37
        assert op["detector_baseline"]["tp"] == 0
        assert op["detector_baseline"]["fp"] == 37
        assert op["detector_baseline"]["fn"] == 92


def test_v2_09c_2_freeze_file_call_count_updated():
    assert BENCHMARK_FREEZE_PATH.exists()
    freeze = json.loads(BENCHMARK_FREEZE_PATH.read_text(encoding="utf-8"))
    assert freeze["real_test_vlm_call_count"] == 474
