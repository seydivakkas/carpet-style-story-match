"""
V2-09C.0 Small-VLM Visual Verifier Preflight & Contract Tests.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
import hashlib
from pathlib import Path
import pytest
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from packages.synthetic_motifs.verifier_compositor import compose_verifier_input, COMPOSITOR_VERSION

ROOT_DIR = Path(__file__).resolve().parents[3]


# Pydantic Contracts for V2-09C Visual Verifier
ALLOWED_KEYS = {
    "eight_pointed_star",
    "geometric_rosette",
    "stepped_polygon_medallion",
    "latchhook_diamond",
    "serrated_leaf",
    "stylized_carnation",
    "geometrized_tulip",
    "tree_of_life_branching",
    "comb_form",
    "hands_on_hips_form",
    "running_water_meander",
    "hooked_lozenge",
    "ram_horn_spiral",
    "cross_star_variant",
    "hexagonal_motif",
    "star_medallion_composite",
    "border_guard_stripe_element"
}


class VisualVerificationResult(BaseModel, extra="forbid"):
    schema_version: str = Field("visual-verifier-v1.0.0", frozen=True)
    proposal_id: str
    decision: str
    proposed_visual_candidate_key: str
    verified_visual_candidate_key: str | None = None
    visual_evidence: str
    abstention_reason: str | None = None
    model_provenance: str | None = None

    def validate_keys_and_semantics(self):
        if self.decision not in {"ACCEPT", "REJECT", "ABSTAIN"}:
            raise ValueError(f"Invalid decision: {self.decision}")
        if self.proposed_visual_candidate_key not in ALLOWED_KEYS:
            raise ValueError(f"Invalid proposed key: {self.proposed_visual_candidate_key}")
        if self.decision == "ACCEPT":
            if self.verified_visual_candidate_key not in ALLOWED_KEYS:
                raise ValueError("ACCEPT decision requires a valid 17-key verified_visual_candidate_key")
        else:
            if self.verified_visual_candidate_key is not None:
                raise ValueError("REJECT/ABSTAIN decision must have verified_visual_candidate_key = None")


class VisualVerifierBenchmarkCase(BaseModel, extra="forbid"):
    case_id: str
    dataset_layer: str
    source_image_id: str
    proposal_id: str
    proposed_key: str
    expected_case_type: str
    gt_visual_key: str | None = None
    input_artifact_ref: str
    detector_provenance: str | None = None


class VisualVerifierBenchmarkResult(BaseModel, extra="forbid"):
    candidate_id: str
    case_count: int
    schema_valid_count: int
    accept_count: int
    reject_count: int
    abstain_count: int
    coverage: float
    selective_accuracy: float
    precision_lift: float
    recall_cost: float
    hard_negative_rejection_rate: float


def test_v2_09c_model_candidates_manifest():
    path = ROOT_DIR / "data" / "vlm" / "v2-09c-model-candidates-v1.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["manifest_version"] == "v2-09c-model-candidates-v1.0.0"
    candidates = {c["candidate_id"]: c for c in data["candidates"]}
    assert "R0" in candidates
    assert "C1" in candidates
    assert "C2" in candidates
    assert "C3" in candidates

    assert candidates["R0"]["model_id"] == "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"
    assert candidates["C1"]["model_id"] == "Qwen/Qwen3-VL-2B-Instruct"
    assert candidates["C2"]["model_id"] == "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
    assert candidates["C3"]["model_id"] == "Qwen/Qwen2-VL-2B-Instruct"

    for c_id, c_data in candidates.items():
        assert c_data["license_id"] == "apache-2.0"
        assert c_data["manual_gate_required"] is False

    excluded = {c["candidate_id"]: c for c in data["excluded_candidates"]}
    assert "EX1" in excluded
    assert excluded["EX1"]["reason"] == "MANUAL_LICENSE_GATE"


def test_v2_09c_download_plan():
    path = ROOT_DIR / "data" / "vlm" / "v2-09c-download-plan-v1.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "MODEL_DOWNLOAD_APPROVAL_REQUIRED"
    assert data["downloads_executed"] is False
    assert data["paligemma_included"] is False
    assert data["storage_preflight"] == "PASS_FITS_DISK"
    assert len(data["proposed_models_for_approval"]) == 4


def test_v2_09c_schema_and_policy():
    schema_path = ROOT_DIR / "data" / "schemas" / "visual-verifier-v1.schema.json"
    policy_path = ROOT_DIR / "data" / "vlm" / "visual-verifier-benchmark-policy-v1.json"

    assert schema_path.exists()
    assert policy_path.exists()

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["additionalProperties"] is False

    with open(policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)
    assert policy["policy_version"] == "visual-verifier-benchmark-policy-v1.0.0"
    assert len(policy["candidate_set"]) == 4


def test_v2_09c_prompt_artifacts():
    txt_path = ROOT_DIR / "data" / "vlm" / "prompts" / "motif-visual-verifier-prompt-v1.txt"
    json_path = ROOT_DIR / "data" / "vlm" / "prompts" / "motif-visual-verifier-prompt-v1.json"

    assert txt_path.exists()
    assert json_path.exists()

    txt_content = txt_path.read_text(encoding="utf-8")
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    computed_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    assert meta["sha256"] == computed_hash
    assert meta["chain_of_thought"] is False
    assert meta["cultural_reasoning"] is False
    assert meta["allowed_keys_count"] == 17

    # Verify 17 keys are listed in prompt text
    for key in ALLOWED_KEYS:
        assert key in txt_content

    # Verify forbidden words are absent
    forbidden_terms = ["Seljuk", "Ottoman", "protection", "fertility", "meaning", "symbolism", "religion"]
    for term in forbidden_terms:
        assert term not in txt_content


def test_v2_09c_input_compositor_determinism():
    test_img = Image.new("RGB", (800, 600), color=(180, 120, 80))
    bbox = [100.0, 150.0, 300.0, 400.0]

    img1, hash1 = compose_verifier_input(test_img, bbox, "prop_1", "eight_pointed_star")
    img2, hash2 = compose_verifier_input(test_img, bbox, "prop_1", "eight_pointed_star")

    assert img1.size == (672, 448)
    assert hash1 == hash2


def test_v2_09c_verifier_contracts_pydantic():
    # Valid ACCEPT
    res_accept = VisualVerificationResult(
        proposal_id="p1",
        decision="ACCEPT",
        proposed_visual_candidate_key="eight_pointed_star",
        verified_visual_candidate_key="eight_pointed_star",
        visual_evidence="Eight radial triangular star points around central axis."
    )
    res_accept.validate_keys_and_semantics()

    # Valid REJECT
    res_reject = VisualVerificationResult(
        proposal_id="p2",
        decision="REJECT",
        proposed_visual_candidate_key="latchhook_diamond",
        verified_visual_candidate_key=None,
        visual_evidence="Generic background stripe without latchhooks."
    )
    res_reject.validate_keys_and_semantics()

    # Extra cultural field forbidden
    with pytest.raises(ValidationError):
        VisualVerificationResult(
            proposal_id="p3",
            decision="ACCEPT",
            proposed_visual_candidate_key="eight_pointed_star",
            verified_visual_candidate_key="eight_pointed_star",
            visual_evidence="Eight radial points.",
            culture="Anatolian"  # FORBIDDEN
        )

    # Invalid verified key when REJECT
    with pytest.raises(ValueError):
        invalid_res = VisualVerificationResult(
            proposal_id="p4",
            decision="REJECT",
            proposed_visual_candidate_key="eight_pointed_star",
            verified_visual_candidate_key="eight_pointed_star",
            visual_evidence="Rejected"
        )
        invalid_res.validate_keys_and_semantics()
