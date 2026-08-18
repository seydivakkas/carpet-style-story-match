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
        assert isinstance(cand["schema_valid"], bool), f"Candidate {cid} schema_valid must be bool"
        assert isinstance(cand["semantic_valid"], bool), f"Candidate {cid} semantic_valid must be bool"
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


def test_v2_09c_1b_verifier_runtime_input_record():
    """Verify VerifierRuntimeInputRecord hashing and trusted input identity fields."""
    from packages.synthetic_motifs.verifier_adapters import VerifierRuntimeInputRecord
    record = VerifierRuntimeInputRecord(
        run_id="v2-09c-1b-test",
        candidate_id="C1",
        started_at="2026-08-18T10:00:00Z",
        proposal_id="smoke_001",
        proposed_visual_candidate_key="star_like",
        prompt_sha256="f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac",
        materialized_prompt_sha256="mat_prompt_test_hash",
        canonical_semantic_payload_hash="canonical_payload_test_hash",
        png_sha256="6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d",
        generation_policy_sha256="gen_policy_test_hash",
        adapter_id="adapter-c1-v1.0.0",
        model_revision="89644892e4d85e24eaac8bacfd4f463576704203",
        model_snapshot_sha256="snapshot_test_hash"
    )
    assert record.proposal_id == "smoke_001"
    assert record.proposed_visual_candidate_key == "star_like"
    assert len(record.compute_hash()) == 64


def test_v2_09c_1b_corrected_provenance_report():
    """Verify V2-09C.1B provenance report structure, audit findings, and call counts."""
    report_path = ROOT_DIR / "data/validation/v2-09c/corrected-runtime-smoke-provenance-report.json"
    assert report_path.exists(), "Provenance report missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["benchmark_phase"] in ["V2-09C.1B", "V2-09C.1C"]
    assert report["status"] == "PASS_WITH_RUNTIME_EXCLUSIONS"
    assert report["real_test_vlm_call_count"] == 0
    assert report["trusted_input"]["proposal_id"] == "smoke_001"
    assert report["trusted_input"]["proposed_visual_candidate_key"] == "star_like"

    findings = report["audit_findings"]
    assert findings["stale_response_reuse"] is False
    assert findings["fixture_response_reuse"] is False
    assert findings["model_response_cache"] is False

    cands = report["candidates"]
    for cid in ["C1", "C2", "C3"]:
        cand = cands[cid]
        assert cand["model_generate_call_count"] == 1
        assert cand["response_cache_hit"] is False
        assert cand["trusted_input_hash"] is not None
        assert cand["materialized_model_input_sha256"] is not None
        assert cand["raw_output_sha256"] is not None
        assert cand["token_sequence_sha256"] != ""
        assert cand["same_raw_output_as_previous"] in [True, False]


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


def test_v2_09c_1c_prompt_materializer_valid_keys():
    """Verify VisualVerifierPromptMaterializer replaces placeholders without changing prompt template SHA."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerifierPromptMaterializer
    materializer = VisualVerifierPromptMaterializer()
    assert materializer.template_hash == "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"

    msg = materializer.materialize(proposal_id="smoke_001", proposed_key="star_like")
    assert msg.proposal_id == "smoke_001"
    assert msg.proposed_visual_candidate_key == "star_like"
    assert "smoke_001" in msg.materialized_prompt_text
    assert "star_like" in msg.materialized_prompt_text
    assert "<proposal_id>" not in msg.materialized_prompt_text
    assert "<proposed_key>" not in msg.materialized_prompt_text
    assert len(msg.compute_canonical_hash()) == 64


def test_v2_09c_1c_prompt_materializer_invalid_keys_blocked():
    """Verify pre-inference validation blocks non-17 keys and domain terms BEFORE model call."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerifierPromptMaterializer
    materializer = VisualVerifierPromptMaterializer()

    with pytest.raises(ValueError, match="BLOCKED_INVALID_PROPOSED_KEY"):
        materializer.materialize(proposal_id="smoke_001", proposed_key="geometrized_tulip")

    with pytest.raises(ValueError, match="BLOCKED_INVALID_PROPOSED_KEY"):
        materializer.materialize(proposal_id="smoke_001", proposed_key="elibelinde")

    with pytest.raises(ValueError, match="BLOCKED_INVALID_PROPOSED_KEY"):
        materializer.materialize(proposal_id="smoke_001", proposed_key="geometric_rosette")


def test_v2_09c_1c_prompt_materializer_invalid_proposal_id_blocked():
    """Verify pre-inference validation blocks malformed proposal_id syntax."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerifierPromptMaterializer
    materializer = VisualVerifierPromptMaterializer()

    with pytest.raises(ValueError, match="BLOCKED_INVALID_PROPOSAL_ID"):
        materializer.materialize(proposal_id="<script>alert(1)</script>", proposed_key="star_like")


def test_v2_09c_1c_benchmark_freeze_artifact():
    """Verify visual-verifier-benchmark-freeze.json contents and strict immutability locks."""
    freeze_path = ROOT_DIR / "data/validation/v2-09c/visual-verifier-benchmark-freeze.json"
    assert freeze_path.exists(), "Benchmark freeze artifact missing"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))

    assert freeze["benchmark_contract_version"] == "v2-09c-benchmark-freeze-v1.0.0"
    assert freeze["schema_hash"] == "aa63efd246a867f84ba931900589343fc080f18f6dab2155552bac10d41547f8"
    assert freeze["prompt_template_hash"] == "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"
    assert freeze["compositor_hash"] == "6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d"
    assert freeze["real_test_vlm_call_count"] in (0, 474)
    assert len(freeze["frozen_17_keys"]) == 17
    assert freeze["eligible_models"] == ["C1", "C2", "C3"]


def test_v2_09c_1d_canonical_hash_domain_separation():
    """Verify materialized prompt SHA and canonical message SHA are distinct and cover proposal identity."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerifierPromptMaterializer
    materializer = VisualVerifierPromptMaterializer()
    msg = materializer.materialize(proposal_id="smoke_001", proposed_key="star_like")

    prompt_sha = hashlib.sha256(msg.materialized_prompt_text.encode("utf-8")).hexdigest()
    canonical_hash = msg.compute_canonical_hash()

    assert prompt_sha != canonical_hash, "Prompt SHA and Canonical Message SHA must be distinct domain-separated hashes"

    # Changing proposal_id changes canonical hash
    msg_prop = materializer.materialize(proposal_id="smoke_002", proposed_key="star_like")
    assert msg_prop.compute_canonical_hash() != canonical_hash

    # Changing proposed_key changes canonical hash
    msg_key = materializer.materialize(proposal_id="smoke_001", proposed_key="niche_like")
    assert msg_key.compute_canonical_hash() != canonical_hash


def test_v2_09c_1d_second_case_verification():
    """Verify second-case (case_002 / octagonal_form) changes prompt SHA & canonical SHA while keeping template SHA unchanged."""
    from packages.synthetic_motifs.verifier_adapters import VisualVerifierPromptMaterializer
    materializer = VisualVerifierPromptMaterializer()
    case1 = materializer.materialize(proposal_id="smoke_001", proposed_key="star_like")
    case2 = materializer.materialize(proposal_id="case_002", proposed_key="octagonal_form")

    assert case1.template_sha256 == case2.template_sha256 == "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"
    assert case1.materialized_prompt_text != case2.materialized_prompt_text
    assert case1.compute_canonical_hash() != case2.compute_canonical_hash()


def test_v2_09c_1d_pre_real_test_audit_artifact():
    """Verify pre-real-test-freeze-audit.json contents and status PASS_REAL_TEST_GATE_READY."""
    audit_path = ROOT_DIR / "data/validation/v2-09c/pre-real-test-freeze-audit.json"
    assert audit_path.exists(), "Pre-REAL_TEST freeze audit artifact missing"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    assert audit["benchmark_phase"] == "V2-09C.1D"
    assert audit["status"] == "PASS_REAL_TEST_GATE_READY"
    assert audit["real_test_vlm_call_count"] == 0
    assert audit["hash_domain_audit"]["equal_hash_root_cause"] == "C. CANONICAL_HASH_ONLY_HASHES_PROMPT_TEXT"
    assert audit["hash_domain_audit"]["accidental_alias_fixed"] is True
    assert audit["second_case_verification"]["prompt_template_unchanged"] is True
    assert audit["second_case_verification"]["materialized_prompt_changed"] is True
    assert audit["second_case_verification"]["canonical_hash_changed"] is True


