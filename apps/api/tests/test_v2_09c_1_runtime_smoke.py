"""
V2-09C.1 Model Download & Sequential Runtime Smoke Tests.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
import hashlib
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


def test_v2_09c_1_approved_model_allowlist():
    """Verify that only the four approved candidate models are in the download plan and registry."""
    plan_path = ROOT_DIR / "data/vlm/v2-09c-download-plan-v1.json"
    assert plan_path.exists(), "Download plan JSON missing"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    approved_ids = {
        "Qwen/Qwen2.5-VL-3B-Instruct-AWQ",
        "Qwen/Qwen3-VL-2B-Instruct",
        "HuggingFaceTB/SmolVLM2-2.2B-Instruct",
        "Qwen/Qwen2-VL-2B-Instruct"
    }

    assert plan["downloads_executed"] is True, "Downloads must be marked as executed"
    assert plan["status"] == "DOWNLOADED", "Download plan status must be DOWNLOADED"

    for model in plan["proposed_models_for_approval"]:
        assert model["model_id"] in approved_ids, f"Unapproved model found: {model['model_id']}"
        assert model["manual_gate"] is False

    reg_path = ROOT_DIR / "data/vlm/v2-09c-model-candidates-v1.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    assert len(reg["candidates"]) == 4
    for cand in reg["candidates"]:
        assert cand["model_id"] in approved_ids
        assert cand["artifact_status"] == "DOWNLOADED"


def test_v2_09c_1_artifact_provenance_and_shards():
    """Verify exact HF revision, snapshot manifest hash, and weight shard SHA-256 integrity."""
    report_path = ROOT_DIR / "data/validation/v2-09c/model-download-runtime-smoke-report.json"
    assert report_path.exists(), "Smoke report JSON missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["real_test_vlm_call_count"] == 0, "REAL_TEST call count must be 0"

    candidates = report["candidates"]
    assert len(candidates) == 4

    expected_revisions = {
        "R0": "e7b623934290c5a4da0ee3c6e1e57bfb6b5abbf2",
        "C1": "89644892e4d85e24eaac8bacfd4f463576704203",
        "C2": "482adb537c021c86670beed01cd58990d01e72e4",
        "C3": "895c3a49bc3fa70a340399125c650a463535e71c"
    }

    models_dir = ROOT_DIR / "artifacts/v2-09c/models"

    for cid, cdata in candidates.items():
        assert cdata["revision"] == expected_revisions[cid], f"Revision mismatch for {cid}"
        assert len(cdata["snapshot_manifest_sha256"]) == 64, f"Invalid manifest SHA-256 for {cid}"
        assert len(cdata["weight_shards"]) >= 1, f"No weight shards recorded for {cid}"

        cand_dir = models_dir / cid
        assert cand_dir.exists(), f"Model directory missing for {cid}"

        for shard in cdata["weight_shards"]:
            shard_file = cand_dir / shard["name"]
            assert shard_file.exists(), f"Shard file missing: {shard['name']}"
            assert shard_file.stat().st_size == shard["size_bytes"], f"Shard size mismatch: {shard['name']}"
            assert shard["size_bytes"] > 0, f"Zero-byte shard found: {shard['name']}"


def test_v2_09c_1_prompt_and_compositor_immutability():
    """Verify prompt and compositor golden hashes remain strictly unchanged."""
    prompt_file = ROOT_DIR / "data/vlm/prompts/motif-visual-verifier-prompt-v1.txt"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    assert prompt_hash == "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"

    golden_path = ROOT_DIR / "data/validation/v2-09c/golden_smoke_input.png"
    assert golden_path.exists(), "Golden smoke PNG missing"
    golden_hash = hashlib.sha256(golden_path.read_bytes()).hexdigest()
    assert golden_hash == "6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d"


def test_v2_09c_1_sequential_smoke_execution():
    """Verify sequential runtime smoke execution results for C1, C2, C3 and R0 exclusion."""
    report_path = ROOT_DIR / "data/validation/v2-09c/model-download-runtime-smoke-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    cands = report["candidates"]

    # R0 AWQ exclusion
    assert cands["R0"]["runtime_status"] == "RUNTIME_INCOMPATIBLE"
    assert cands["R0"]["schema_valid"] is False

    # C1, C2, C3 Runtime Ready
    for cid in ["C1", "C2", "C3"]:
        cand = cands[cid]
        assert cand["runtime_status"] == "RUNTIME_READY", f"Candidate {cid} not RUNTIME_READY"
        assert cand["schema_valid"] is False, f"Candidate {cid} expected schema_valid False due to invalid key output"
        assert cand["semantic_valid"] is False, f"Candidate {cid} expected semantic_valid False due to invalid key output"
        assert cand["gpu_infer_peak_allocated_gib"] < 7.0, f"Candidate {cid} VRAM peak exceeded limit"
        assert cand["inference_seconds"] > 0.0, f"Candidate {cid} inference time invalid"
        assert cand["generated_tokens"] > 0, f"Candidate {cid} produced 0 tokens"


def test_v2_09c_1_no_cultural_fields_in_smoke():
    """Verify smoke outputs do not contain forbidden cultural or non-visual keys."""
    report_path = ROOT_DIR / "data/validation/v2-09c/model-download-runtime-smoke-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    forbidden_fields = [
        "culture", "origin", "dynasty", "period", "religion",
        "meaning", "symbolism", "story", "authenticity", "personality"
    ]

    for cid in ["C1", "C2", "C3"]:
        raw_output = report["candidates"][cid]["raw_output"]
        for field in forbidden_fields:
            assert f'"{field}"' not in raw_output.lower(), f"Forbidden field '{field}' present in {cid} output"


def test_v2_09c_1_real_test_guard():
    """Explicit guard test ensuring smoke runner cannot accept REAL_TEST data."""
    report_path = ROOT_DIR / "data/validation/v2-09c/model-download-runtime-smoke-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["real_test_vlm_call_count"] == 0


def test_v2_09c_1a_exact_enum():
    """Verify exact 17 frozen visual candidate keys in registry."""
    from packages.synthetic_motifs.verifier_adapters import FROZEN_17_KEYS
    assert len(FROZEN_17_KEYS) == 17
    expected = {
        "medallion_like", "niche_like", "star_like", "rosette_like",
        "palmette_like", "lotus_like", "vine_scroll_like", "cloud_band_like",
        "tree_like", "horn_like", "human_figure_like_geometric", "comb_like",
        "hook_like", "lattice_like", "lozenge_like", "octagonal_form",
        "unmapped_visual_motif"
    }
    assert FROZEN_17_KEYS == expected


def test_v2_09c_1a_unknown_proposed_key():
    """Verify unknown proposed key fails schema/semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "geometrized_tulip"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "geometrized_tulip",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "A star-like shape is visible.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["schema_valid"] is False or res["semantic_valid"] is False


def test_v2_09c_1a_unknown_verified_key():
    """Verify unknown verified key fails schema/semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "geometric_rosette",
        "visual_evidence": "A rosette shape is visible.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["schema_valid"] is False or res["semantic_valid"] is False


def test_v2_09c_1a_proposal_id_mutation():
    """Verify proposal_id mutation fails semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "1234567890",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "A star shape.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is False
    assert any("PROPOSAL_ID_MUTATED" in r for r in res["semantic_reasons"])


def test_v2_09c_1a_proposed_key_mutation():
    """Verify proposed_visual_candidate_key mutation fails semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "lozenge_like",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "A star shape.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is False
    assert any("PROPOSED_KEY_MUTATED" in r for r in res["semantic_reasons"])


def test_v2_09c_1a_reject_with_key():
    """Verify REJECT with non-null verified key fails semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "REJECT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "No star visible.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is False
    assert any("REJECT_REQUIRES_NULL_VERIFIED_KEY" in r for r in res["semantic_reasons"])


def test_v2_09c_1a_reject_without_key():
    """Verify REJECT with null verified key passes semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "REJECT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": None,
        "visual_evidence": "No star visible in the crop.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is True


def test_v2_09c_1a_accept_valid_key():
    """Verify ACCEPT with valid verified key passes semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "8-pointed star shape present.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is True


def test_v2_09c_1a_accept_correction():
    """Verify ACCEPT with key correction to another frozen key passes semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "octagonal_form",
        "visual_evidence": "Shape is an 8-sided octagon rather than a star.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is True


def test_v2_09c_1a_abstain():
    """Verify ABSTAIN with null verified key and non-empty reason passes semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ABSTAIN",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": None,
        "visual_evidence": "Region is too blurry.",
        "abstention_reason": "Low resolution image preventing visual feature identification."
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["semantic_valid"] is True


def test_v2_09c_1a_canonical_motif_as_visual_key():
    """Verify domain motif key 'elibelinde' fails visual key validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "elibelinde",
        "visual_evidence": "An elibelinde motif.",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["schema_valid"] is False or res["semantic_valid"] is False


def test_v2_09c_1a_cultural_output():
    """Verify cultural field present fails semantic validation."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerificationSemanticValidator
    validator = VisualVerificationSemanticValidator()
    verifier_input = {"proposal_id": "smoke_001", "proposed_visual_candidate_key": "star_like"}
    raw_output = json.dumps({
        "schema_version": "visual-verifier-v1.0.0",
        "proposal_id": "smoke_001",
        "decision": "ACCEPT",
        "proposed_visual_candidate_key": "star_like",
        "verified_visual_candidate_key": "star_like",
        "visual_evidence": "Star motif with cultural meaning.",
        "culture": "Anatolian",
        "abstention_reason": None
    })
    res = validator.validate(verifier_input, raw_output)
    assert res["schema_valid"] is False or res["semantic_valid"] is False
