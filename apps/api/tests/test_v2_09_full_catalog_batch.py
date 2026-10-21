"""Unit and Integration Tests for V2-09 Final Full Catalog Motif Research Batch & Report Integrity."""

import json
import pytest
from pathlib import Path
from packages.synthetic_motifs.cli import load_class_map

ROOT_DIR = Path(__file__).resolve().parents[3]  # Çalışma dizininden bağımsız, depo kökü
MANIFEST_PATH = ROOT_DIR / "data" / "validation" / "v2-09" / "catalog-motif-batch-input-manifest.json"
RESULT_PATH = ROOT_DIR / "data" / "validation" / "v2-09" / "catalog-motif-batch-result-v1.json"
AUDIT_PATH = ROOT_DIR / "data" / "validation" / "v2-09" / "catalog-motif-batch-integrity-audit.json"
REPORT_INTEGRITY_AUDIT_PATH = ROOT_DIR / "data" / "validation" / "v2-09" / "catalog-motif-batch-report-integrity-audit.json"
ACCEPTANCE_PATH = ROOT_DIR / "data" / "validation" / "v2-09" / "v2-09-final-acceptance.json"

RAW_DETECT_PATH = ROOT_DIR / "artifacts" / "v2-09-final" / "catalog-batch" / "detect-raw-proposals.json"
RAW_OBB_PATH = ROOT_DIR / "artifacts" / "v2-09-final" / "catalog-batch" / "obb-raw-proposals.json"

EXPECTED_NO_IMAGE_SKUS = ["73480 070", "74480 070", "74928 062", "74928 957", "75272 060"]
EXPECTED_DETECT_HASH = "085fc5d9d2427562d908065f64ce5a9318ad645133e95c3558cba4ab861cd44d"
EXPECTED_OBB_HASH = "f0ddfd1ef6cbd4a5cab366b0172e65d25d941710f90d865264b666ac41056f21"
EXPECTED_THRESHOLD = 0.25


def test_v2_09_catalog_input_manifest_universe():
    """Verify input manifest contains 232 total products, 227 processable, and 5 no-image SKUs."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_catalog_products"] == 232
    assert data["processable_images"] == 227
    assert data["no_primary_image_count"] == 5
    assert sorted(data["no_primary_skus"]) == sorted(EXPECTED_NO_IMAGE_SKUS)
    assert len(data["records"]) == 232


def test_v2_09_catalog_result_artifacts_exist_and_valid():
    """Verify result, audit, report integrity audit, and final acceptance artifacts exist and maintain contract invariants."""
    assert RESULT_PATH.exists()
    assert AUDIT_PATH.exists()
    assert REPORT_INTEGRITY_AUDIT_PATH.exists()
    assert ACCEPTANCE_PATH.exists()

    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        res = json.load(f)

    assert res["universe"]["total_catalog_products"] == 232
    assert res["universe"]["processable_images"] == 227
    assert res["universe"]["no_primary_image_count"] == 5
    assert sorted(res["universe"]["no_primary_skus"]) == sorted(EXPECTED_NO_IMAGE_SKUS)


def test_v2_09_per_image_raw_records_and_zero_proposals_accounting():
    """Verify exact 227 per-image raw result records for Detect and OBB with sum(proposals) == 0."""
    assert RAW_DETECT_PATH.exists()
    assert RAW_OBB_PATH.exists()

    with open(RAW_DETECT_PATH, "r", encoding="utf-8") as f:
        d_map = json.load(f)

    with open(RAW_OBB_PATH, "r", encoding="utf-8") as f:
        o_map = json.load(f)

    assert len(d_map) == 227
    assert len(o_map) == 227
    assert sum(v["proposal_count"] for v in d_map.values()) == 0
    assert sum(v["proposal_count"] for v in o_map.values()) == 0


def test_v2_09_same_227_images_and_accounting_both_streams():
    """Verify Detect and OBB streams processed identical 227 images with 100% success."""
    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        res = json.load(f)

    detect = res["streams"]["detect"]
    obb = res["streams"]["obb"]

    assert detect["attempted"] == 227
    assert detect["successful"] == 227
    assert detect["failed"] == 0
    assert detect["model_hash"] == EXPECTED_DETECT_HASH
    assert detect["threshold"] == EXPECTED_THRESHOLD

    assert obb["attempted"] == 227
    assert obb["successful"] == 227
    assert obb["failed"] == 0
    assert obb["model_hash"] == EXPECTED_OBB_HASH
    assert obb["threshold"] == EXPECTED_THRESHOLD


def test_v2_09_17_keys_registry_and_class_id_mapping():
    """Verify all class distribution keys belong to frozen 17-key registry and match 0..16 class IDs."""
    class_map = load_class_map()
    valid_keys = set(class_map.keys())
    assert len(valid_keys) == 17
    assert set(class_map.values()) == set(range(17))

    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        res = json.load(f)

    for stream_name in ["detect", "obb"]:
        stream = res["streams"][stream_name]
        dist = stream["class_distribution"]
        assert set(dist.keys()) == valid_keys
        assert sum(dist.values()) == stream["total_proposals"]


def test_v2_09_review_burden_buckets_sum_to_227():
    """Verify review burden buckets (0, 1, 2-5, 6-10, >10) sum to exactly 227 processable images."""
    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        res = json.load(f)

    for stream_name in ["detect", "obb"]:
        buckets = res["streams"][stream_name]["review_burden_buckets"]
        assert sum(buckets.values()) == 227


def test_v2_09_hash_provenance_and_single_run_telemetry_lineage():
    """Verify hash-domain labels and single coherent run telemetry lineage in integrity audit artifact."""
    with open(REPORT_INTEGRITY_AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    hash_prov = audit["hash_provenance"]
    assert hash_prov["frozen_key_set_hash_domain"] == "SERIALIZED_DICT_SHA256"
    assert hash_prov["class_map_file_bytes_hash_domain"] == "FILE_BYTES_SHA256"
    assert hash_prov["manifest_canonical_hash_domain"] == "CANONICAL_MANIFEST_FINGERPRINT"
    assert hash_prov["manifest_file_bytes_hash_domain"] == "FILE_BYTES_SHA256"

    run_prov = audit["run_provenance"]
    assert run_prov["single_coherent_run"] is True
    assert run_prov["batch_run_id"] == "v2-09-final-catalog-20260818"


def test_v2_09_no_unsupported_precision_or_false_positive_claims():
    """Verify no unsupported precision or false-positive claims are present in result or documentation artifacts."""
    with open(REPORT_INTEGRITY_AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    sci = audit["scientific_interpretation"]
    assert sci["catalog_gt_available"] is False
    assert sci["precision_measured"] is False
    assert sci["recall_measured"] is False
    assert sci["false_positive_count_measured"] is False

    # Check documentation text for forbidden false precision claims
    doc_path = ROOT_DIR / "docs" / "V2_09_FULL_CATALOG_BATCH_CLOSURE.md"
    assert doc_path.exists()
    with open(doc_path, "r", encoding="utf-8") as f:
        doc_text = f.read()

    assert "zero false-positive proposals" not in doc_text
    assert "proves high precision" not in doc_text
    assert "confirms zero noise" not in doc_text


def test_v2_09_no_vlm_no_db_write_no_cultural_fields():
    """Verify zero VLM calls, zero production DB writes, zero cultural target fields, and no winner assignment."""
    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        res = json.load(f)

    # Zero VLM & DB Writes
    assert res["historical_vlm_accounting"]["full_catalog_vlm_calls"] == 0
    assert res["historical_vlm_accounting"]["new_vlm_calls"] == 0
    assert res["production_impact"]["production_db_writes"] == 0
    assert res["production_impact"]["cultural_claims_generated"] == 0
    assert res["production_impact"]["stories_generated"] == 0
    assert res["production_impact"]["vlm_verifier_selected"] is None

    # No forbidden cultural fields in result root or stream summaries
    forbidden_words = ["meaning", "symbolism", "culture", "origin", "dynasty", "religion", "authenticity", "story", "personality"]
    serialized = json.dumps(res, ensure_ascii=False)
    for word in forbidden_words:
        assert f'"{word}"' not in serialized

    # No single detector winner assigned
    assert "winner" not in res
    assert "rank" not in res
    assert "overall_score" not in res
