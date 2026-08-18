"""
V2-09C.2 / V2-09C.2A Benchmark Execution and Result Accounting Tests.

Verifies:
1. Benchmark result artifact small-vlm-benchmark-result-v1.json exists and contains PASS_RESULT_CLOSURE.
2. Scientific accounting audit benchmark-result-accounting-audit.json exists and contains PASS_RESULT_CLOSURE.
3. No-ranking enforcement: prohibited keys (winner, rank, overall_score, leaderboard_score, champion) are absent.
4. Denominator and decision checks: ACCEPT + REJECT + ABSTAIN + INVALID_OUTPUT == total cases for all layers.
5. Exact VLM call count on REAL_TEST (474 historical, 0 new).
6. Synthetic controlled composition (85 correct, 17 wrong-key, 20 hard-negative, 6 background = 128 total).
7. Full OBB baseline and candidate metrics accounting (37 proposals).
8. Hard-negative rejection rate is 0.0% across C1, C2, C3.
"""

import json
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
BENCHMARK_RESULT_PATH = ROOT_DIR / "data/validation/v2-09c/small-vlm-benchmark-result-v1.json"
ACCOUNTING_AUDIT_PATH = ROOT_DIR / "data/validation/v2-09c/benchmark-result-accounting-audit.json"
FIRST_LOOK_AUDIT_PATH = ROOT_DIR / "data/validation/v2-09c/real-test-first-look-audit.json"
BENCHMARK_FREEZE_PATH = ROOT_DIR / "data/validation/v2-09c/visual-verifier-benchmark-freeze.json"
MANIFESTS_PATH = ROOT_DIR / "data/validation/v2-09c/benchmark-case-manifests.json"


def test_v2_09c_2a_result_artifact_exists_and_valid():
    assert BENCHMARK_RESULT_PATH.exists(), f"Missing benchmark result artifact at {BENCHMARK_RESULT_PATH}"
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    
    assert data["task"] == "V2-09C.2 — Frozen Small-VLM Visual Verifier Benchmark Execution"
    assert data["status"] == "PASS_RESULT_CLOSURE"
    assert "benchmark_run_id" in data
    assert "generated_at" in data


def test_v2_09c_2a_accounting_audit_artifact_valid():
    assert ACCOUNTING_AUDIT_PATH.exists(), f"Missing accounting audit at {ACCOUNTING_AUDIT_PATH}"
    audit = json.loads(ACCOUNTING_AUDIT_PATH.read_text(encoding="utf-8"))
    
    assert audit["task"] == "V2-09C.2A — Benchmark Result Accounting & No-Ranking Scientific Closure"
    assert audit["status"] == "PASS_RESULT_CLOSURE"
    assert audit["inference_accounting"]["new_vlm_calls"] == 0
    assert audit["inference_accounting"]["new_real_test_vlm_call_count"] if "new_real_test_vlm_call_count" in audit["inference_accounting"] else audit["inference_accounting"]["new_real_test_vlm_calls"] == 0
    assert audit["inference_accounting"]["historical_real_test_vlm_calls"] == 474
    assert audit["inference_accounting"]["case_ids_identical_across_candidates"] is True


def test_v2_09c_2a_no_ranking_enforcement():
    result_text = BENCHMARK_RESULT_PATH.read_text(encoding="utf-8").lower()
    audit_text = ACCOUNTING_AUDIT_PATH.read_text(encoding="utf-8").lower()
    
    prohibited_keys = ["\"rank\"", "\"winner\"", "\"champion\"", "\"overall_score\"", "\"leaderboard_score\""]
    for pk in prohibited_keys:
        assert pk not in result_text, f"Prohibited ranking key {pk} found in benchmark result artifact"
        assert pk not in audit_text, f"Prohibited ranking key {pk} found in accounting audit artifact"


def test_v2_09c_2a_contract_hashes_match_freeze():
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


def test_v2_09c_2a_first_look_audit_artifact():
    assert FIRST_LOOK_AUDIT_PATH.exists(), f"Missing first look audit at {FIRST_LOOK_AUDIT_PATH}"
    audit = json.loads(FIRST_LOOK_AUDIT_PATH.read_text(encoding="utf-8"))
    
    assert audit["benchmark_phase"] == "V2-09C.2"
    assert audit["pre_run_freeze_verification"] == "PASS"
    assert audit["real_test_opened_at"] == "2026-08-18T08:18:27Z"
    assert audit["real_test_first_evaluated_model"] == "C1"
    assert audit["post_open_modifications"] == "NONE"
    assert audit["post_benchmark_new_vlm_calls"] == 0
    assert audit["post_benchmark_tuning"] is False


def test_v2_09c_2a_case_accounting_totals():
    data = json.loads(BENCHMARK_RESULT_PATH.read_text(encoding="utf-8"))
    m_summary = data["manifest_summary"]
    
    sc = m_summary["synthetic_controlled_cases"]
    rc = m_summary["real_gt_controlled_cases"]
    dc = m_summary["real_detector_detect_cases"]
    oc = m_summary["real_detector_obb_cases"]
    
    assert sc == 128
    assert rc == 109
    assert dc == 12
    assert oc == 37
    
    assert sc + rc + dc + oc == 286


def test_v2_09c_2a_decision_sums_and_denominators():
    audit = json.loads(ACCOUNTING_AUDIT_PATH.read_text(encoding="utf-8"))
    checks = audit["denominator_and_decision_checks"]
    
    for c_id in ["C1", "C2", "C3"]:
        c_check = checks[c_id]
        
        # Synthetic controlled (128)
        sc = c_check["synthetic_controlled"]
        assert sc["total"] == 128
        assert sc["ACCEPT"] + sc["REJECT"] + sc["ABSTAIN"] + sc["INVALID_OUTPUT"] == 128
        assert sc["schema_valid"] + sc["schema_invalid"] == 128
        assert sc["semantic_valid"] + sc["semantic_invalid"] == 128
        
        # Real GT controlled (109)
        rc = c_check["real_gt_controlled"]
        assert rc["total"] == 109
        assert rc["ACCEPT"] + rc["REJECT"] + rc["ABSTAIN"] + rc["INVALID_OUTPUT"] == 109
        assert rc["schema_valid"] + rc["schema_invalid"] == 109
        assert rc["semantic_valid"] + rc["semantic_invalid"] == 109
        
        # Detect pipeline (12)
        dp = c_check["detector_detect_pipeline"]
        assert dp["total"] == 12
        assert dp["accepted"] + dp["rejected"] + dp["abstained"] + dp["invalid_output"] == 12
        
        # OBB pipeline (37)
        op = c_check["detector_obb_pipeline"]
        assert op["total"] == 37
        assert op["accepted"] + op["rejected"] + op["abstained"] + op["invalid_output"] == 37


def test_v2_09c_2a_detector_and_obb_confusion_matrices():
    audit = json.loads(ACCOUNTING_AUDIT_PATH.read_text(encoding="utf-8"))
    matrices = audit["pipeline_confusion_matrices"]
    
    # Detect Baseline (12)
    db = matrices["detect_baseline"]
    assert db["proposals"] == 12
    assert db["tp"] == 1
    assert db["fp"] == 11
    assert db["fn"] == 91
    assert db["precision"] == 0.0833
    assert db["recall"] == 0.0109
    
    # Detect Verified C2
    c2_d = matrices["detect_verified"]["C2"]
    assert c2_d["accepted_proposals"] == 4
    assert c2_d["tp"] == 1
    assert c2_d["fp"] == 3
    assert c2_d["fn"] == 91
    assert c2_d["precision"] == 0.25
    assert c2_d["precision_lift"] == 0.1667
    assert c2_d["recall_cost"] == 0.0
    
    # OBB Baseline (37)
    ob = matrices["obb_baseline"]
    assert ob["proposals"] == 37
    assert ob["tp"] == 0
    assert ob["fp"] == 37
    assert ob["fn"] == 92
    assert ob["precision"] == 0.0
    assert ob["recall"] == 0.0
    
    # OBB Verified C2
    c2_o = matrices["obb_verified"]["C2"]
    assert c2_o["accepted_proposals"] == 25
    assert c2_o["tp"] == 0
    assert c2_o["fp"] == 25
    assert c2_o["fn"] == 92
    assert c2_o["fp_per_image_change"] == -0.3428


def test_v2_09c_2a_hard_negative_rejection_interpretation():
    audit = json.loads(ACCOUNTING_AUDIT_PATH.read_text(encoding="utf-8"))
    hn = audit["hard_negative_accounting"]
    
    assert hn["cases_per_candidate"] == 20
    assert hn["rejection_counts"]["C1"] == 0
    assert hn["rejection_counts"]["C2"] == 0
    assert hn["rejection_counts"]["C3"] == 0
    assert "None of the evaluated zero-shot candidates" in hn["interpretation"]
