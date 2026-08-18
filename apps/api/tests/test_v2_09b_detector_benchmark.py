"""
V2-09B Detector Baseline & Real-vs-Synthetic Benchmark Tests.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from packages.synthetic_motifs.proposal import DetectorVisualProposal

ROOT_DIR = Path(__file__).resolve().parents[3]


def test_v2_09b_ultralytics_license_review_artifact():
    path = ROOT_DIR / "data" / "detectors" / "ultralytics-license-review-v1.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["license_status"] == "RESEARCH_EVALUATION_ONLY"
    assert data["research_evaluation_allowed_by_project_policy"] is True
    assert data["production_approved"] is False


def test_v2_09b_detector_baseline_policy_artifact():
    path = ROOT_DIR / "data" / "detectors" / "detector-baseline-policy-v1.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["policy_version"] == "detector-baseline-policy-v1.0.0"
    assert "YOLO11n Detect (yolo11n.pt)" in data["frozen_models"]
    assert "YOLO11n OBB (yolo11n-obb.pt)" in data["frozen_models"]
    assert data["training_parameters"]["seed"] == 42
    assert data["training_parameters"]["imgsz"] == 640


def test_v2_09b_real_motif_benchmark_manifest():
    path = ROOT_DIR / "data" / "datasets" / "real-motif-benchmark-v1" / "manifest.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["benchmark_version"] == "real-motif-benchmark-v1.0.0"
    assert data["split"] == "REAL_TEST"
    assert data["total_images"] >= 30
    assert data["rights_cleared_count"] == data["total_images"]
    
    # Check no duplicate hashes
    hashes = [img["sha256"] for img in data["images"]]
    assert len(hashes) == len(set(hashes))


def test_v2_09b_experiment_manifests_exist():
    detect_path = ROOT_DIR / "data" / "detectors" / "v2-09b-yolo11n-detect-seed42-manifest.json"
    obb_path = ROOT_DIR / "data" / "detectors" / "v2-09b-yolo11n-obb-seed42-manifest.json"

    assert detect_path.exists()
    assert obb_path.exists()

    with open(detect_path, "r", encoding="utf-8") as f:
        d_data = json.load(f)
    assert d_data["experiment_id"] == "v2-09b-yolo11n-detect-seed42"
    assert "metrics_synthetic" in d_data
    assert "metrics_real" in d_data
    assert "domain_gap_mAP50" in d_data

    with open(obb_path, "r", encoding="utf-8") as f:
        o_data = json.load(f)
    assert o_data["experiment_id"] == "v2-09b-yolo11n-obb-seed42"
    assert "metrics_synthetic" in o_data
    assert "metrics_real" in o_data
    assert "domain_gap_mAP50" in o_data


def test_v2_09b_benchmark_report_and_domain_gap():
    path = ROOT_DIR / "data" / "validation" / "v2-09b" / "detector-benchmark-report.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "PASS"
    assert "domain_gap" in data
    assert data["domain_gap"]["detect_mAP50_gap"] > 0.0
    assert data["domain_gap"]["obb_mAP50_gap"] > 0.0
    assert data["hard_negatives"]["positive_label_leakage"] == 0


def test_v2_09b_detector_visual_proposal_contract():
    proposal = DetectorVisualProposal(
        proposal_id="prop_0001",
        visual_candidate_key="star_like",
        confidence=0.88,
        bbox=[10.0, 20.0, 100.0, 120.0],
        model_id="YOLO11n Detect",
        experiment_id="v2-09b-yolo11n-detect-seed42",
        source_image_id="real_carpet_001"
    )
    assert proposal.status == "AI_CANDIDATE"
    assert proposal.visual_candidate_key == "star_like"

    # Verify extra cultural fields are forbidden
    with pytest.raises(ValidationError):
        DetectorVisualProposal(
            proposal_id="prop_0002",
            visual_candidate_key="star_like",
            confidence=0.88,
            bbox=[10.0, 20.0, 100.0, 120.0],
            model_id="YOLO11n Detect",
            experiment_id="v2-09b-yolo11n-detect-seed42",
            source_image_id="real_carpet_001",
            culture="Seljuk"  # FORBIDDEN
        )


def test_v2_09b_1_training_artifact_audit():
    audit_path = ROOT_DIR / "data" / "validation" / "v2-09b" / "training-artifact-audit.json"
    assert audit_path.exists()
    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "PASS"
    assert data["root_cause"]["duplicate_hash_classification"] == "REPORT_ONLY_COPY_ERROR"
    assert data["detect_artifacts"]["base_equals_best"] is False
    assert data["detect_artifacts"]["changed_tensors"] > 0
    assert data["obb_artifacts"]["base_equals_best"] is False
    assert data["obb_artifacts"]["changed_tensors"] > 0
    assert data["real_benchmark_provenance"]["training_overlap"] == 0
    assert len(data["real_benchmark_provenance"]["classes_with_not_enough_support"]) > 0


def test_v2_09b_1_manifest_hash_distinction():
    detect_manifest_path = ROOT_DIR / "data" / "detectors" / "v2-09b-yolo11n-detect-seed42-manifest.json"
    obb_manifest_path = ROOT_DIR / "data" / "detectors" / "v2-09b-yolo11n-obb-seed42-manifest.json"

    with open(detect_manifest_path, "r", encoding="utf-8") as f:
        d_data = json.load(f)
    assert d_data["base_weights_sha256"] != d_data["best_weights_sha256"]
    assert d_data["best_weights_sha256"] != "N/A"

    with open(obb_manifest_path, "r", encoding="utf-8") as f:
        o_data = json.load(f)
    assert o_data["base_weights_sha256"] != o_data["best_weights_sha256"]
    assert o_data["best_weights_sha256"] != "N/A"


def test_v2_09b_2_benchmark_accounting_and_telemetry():
    audit_path = ROOT_DIR / "data" / "validation" / "v2-09b" / "training-artifact-audit.json"
    report_path = ROOT_DIR / "data" / "validation" / "v2-09b" / "detector-benchmark-report.json"

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["benchmark_accounting"]["benchmark_internal_count"] == 57
    assert audit["benchmark_accounting"]["benchmark_passed_checks"] == 57
    assert audit["benchmark_accounting"]["benchmark_failed_checks"] == 0
    assert audit["benchmark_accounting"]["benchmark_wrapper_pytest_count"] == 1

    assert audit["memory_telemetry"]["previous_0_08_gb_classification"] == "INFERENCE_PEAK_POST_TRAINING_IDLE_MEASUREMENT"
    assert audit["memory_telemetry"]["training_memory_scope"] == "ACTUAL_TRAINING_PEAK"
    assert audit["training_duration_telemetry"]["batch_arithmetic_verification"] == "PASS"
    assert audit["latency_telemetry"]["cuda_synchronized"] is True

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["canonical_benchmark_accounting"]["internal_benchmark_checks"] == 57
    assert report["canonical_benchmark_accounting"]["passed_checks"] == 57
    assert report["runtime_telemetry"]["training_memory"]["scope"] == "ACTUAL_TRAINING_PEAK"
    assert report["runtime_telemetry"]["inference_latency"]["cuda_synchronized"] is True


