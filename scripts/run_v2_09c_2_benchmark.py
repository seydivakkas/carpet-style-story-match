"""
V2-09C.2 — Frozen Small-VLM Visual Verifier Benchmark Execution.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import sys
import gc
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
from PIL import Image
import numpy as np
import torch
from ultralytics import YOLO

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
sys.path.insert(0, str(ROOT_DIR))

from packages.synthetic_motifs.cli import load_class_map
from packages.synthetic_motifs.verifier_compositor import compose_verifier_input, COMPOSITOR_VERSION
from packages.synthetic_motifs.verifier_adapters import (
    VisualVerifierPromptMaterializer,
    VisualVerificationSemanticValidator,
    VerifierRuntimeInputRecord,
    CanonicalVerifierMessage,
    Qwen3VLAdapter,
    SmolVLM2Adapter,
    Qwen2VLAdapter,
    Qwen25VLAWQAdapter,
    FROZEN_17_KEYS,
    FROZEN_PROMPT_HASH,
    FROZEN_PNG_HASH,
    MATERIALIZER_VERSION,
    CANONICAL_MESSAGE_CONTRACT,
)

FROZEN_SCHEMA_HASH = "aa63efd246a867f84ba931900589343fc080f18f6dab2155552bac10d41547f8"
FROZEN_17_KEYS_HASH = "b8ac9a720b0f33cc6ebf13e232cabaa9f69f4a67ecf3b91d235ec4ae47efed54"
FROZEN_GENERATION_POLICY_HASH = "58edebf465f41a52c6a413fbf90ad1d84a08e2b980c132b4d07c015660f283a6"
FROZEN_COMPOSITOR_HASH = "6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d"

FROZEN_DETECT_WEIGHTS_HASH = "085fc5d9d2427562d908065f64ce5a9318ad645133e95c3558cba4ab861cd44d"
FROZEN_OBB_WEIGHTS_HASH = "f0ddfd1ef6cbd4a5cab366b0172e65d25d941710f90d865264b666ac41056f21"

FROZEN_CANDIDATE_SNAPSHOTS = {
    "C1": "ccc27a55974c4e0072ba449dc4163a35b5fa9a498410c9831341bdc7c60d227c",
    "C2": "f7568e5a761aa064db58bb09f8a4e4e4a8124993f0939c6d73c794ef9162fcdd",
    "C3": "5ddb0cedc195ecf4b7f401804855f3d7e8e5349ce970e769ac2e6d7e619e8e4a",
    "R0": "97824d4a1d48e483f08fc020b75c4e2dc52de8e2d262000821e9b6ff55de8685"
}

SORTED_17_KEYS = sorted(list(FROZEN_17_KEYS))


def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_box_iou(box1: List[float], box2: List[float]) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    a2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def verify_freeze_state() -> Dict[str, Any]:
    print("--- [1/6] Verifying Pre-Run Benchmark Freeze State ---")
    freeze_json_path = ROOT_DIR / "data/validation/v2-09c/visual-verifier-benchmark-freeze.json"
    if not freeze_json_path.exists():
        raise RuntimeError("BLOCKED_FREEZE_DRIFT: visual-verifier-benchmark-freeze.json not found")

    freeze_data = json.loads(freeze_json_path.read_text(encoding="utf-8"))
    assert freeze_data["schema_hash"] == FROZEN_SCHEMA_HASH, "Schema hash mismatch"
    assert freeze_data["prompt_template_hash"] == FROZEN_PROMPT_HASH, "Prompt template hash mismatch"
    assert freeze_data["compositor_hash"] == FROZEN_COMPOSITOR_HASH, "Compositor hash mismatch"
    assert freeze_data["generation_policy_sha256"] == FROZEN_GENERATION_POLICY_HASH, "Generation policy hash mismatch"
    assert freeze_data["frozen_17_keys_hash"] == FROZEN_17_KEYS_HASH, "17 keys hash mismatch"

    detect_weights = ROOT_DIR / "artifacts/v2-09b/models/yolo11n_detect_seed42/weights/best.pt"
    obb_weights = ROOT_DIR / "artifacts/v2-09b/models/yolo11n_obb_seed42/weights/best.pt"
    assert compute_file_sha256(detect_weights) == FROZEN_DETECT_WEIGHTS_HASH, "Detect weights hash mismatch"
    assert compute_file_sha256(obb_weights) == FROZEN_OBB_WEIGHTS_HASH, "OBB weights hash mismatch"

    # Verify real dataset
    real_dir = ROOT_DIR / "data/datasets/real-motif-benchmark-v1"
    real_manifest = json.loads((real_dir / "manifest.json").read_text(encoding="utf-8"))
    real_rights = json.loads((real_dir / "rights-manifest.json").read_text(encoding="utf-8"))
    real_annots = json.load(open(real_dir / "annotations.json", encoding="utf-8"))["data"]

    assert len(real_manifest["images"]) == 35, f"Expected 35 real images, got {len(real_manifest['images'])}"
    assert sum(len(a["instances"]) for a in real_annots) == 92, f"Expected 92 GT instances, got {sum(len(a['instances']) for a in real_annots)}"
    assert all(r["benchmark_use_allowed"] for r in real_rights["entries"]), "Rights clearance mismatch"

    print("Pre-run freeze state verified PASS!")
    return freeze_data


def build_case_manifests() -> Dict[str, Any]:
    print("--- [2/6] Materializing Bounded Deterministic Benchmark Case Manifests ---")
    cm = load_class_map()
    id_to_class = {v: k for k, v in cm.items()}

    # 1. LAYER A: SYNTHETIC_CONTROLLED (128 cases)
    synth_test_dir = ROOT_DIR / "artifacts/v2-09b/dataset/canonical_json/test"
    synth_img_dir = ROOT_DIR / "artifacts/v2-09b/dataset/yolo_detect/images/test"
    synth_files = sorted(synth_test_dir.glob("*.json"))

    pos_by_class = defaultdict(list)
    hn_by_family = defaultdict(list)
    empty_samples = []

    for f in synth_files:
        d = json.load(open(f, encoding="utf-8"))
        sid = d["sample_id"]
        insts = d.get("instances", [])
        hns = d.get("hard_negatives", [])
        for inst in insts:
            pos_by_class[inst["visual_candidate_key"]].append({"sample_id": sid, "instance": inst})
        for hn in hns:
            hn_by_family[hn["hard_negative_key"]].append({"sample_id": sid, "hn": hn})
        if len(insts) == 0 and len(hns) == 0:
            empty_samples.append(sid)

    synthetic_cases = []
    case_counter = 0

    # 85 Positives (5 per key)
    for k_idx, k in enumerate(SORTED_17_KEYS):
        instances = pos_by_class[k][:5]
        for idx, item in enumerate(instances):
            case_counter += 1
            cid = f"synth_ctrl_pos_{case_counter:03d}"
            inst = item["instance"]
            synthetic_cases.append({
                "case_id": cid,
                "layer": "SYNTHETIC_CONTROLLED",
                "case_type": "CORRECT_PROPOSAL",
                "source_id": item["sample_id"],
                "image_path": str(synth_img_dir / f"{item['sample_id']}.jpg"),
                "proposal_id": f"syn_pos_{k}_{idx+1:02d}",
                "proposed_visual_candidate_key": k,
                "ground_truth_visual_candidate_key": k,
                "bbox_xyxy": inst["bbox_xyxy"],
                "is_negative": False,
                "is_wrong_key": False
            })

    # 17 Wrong-Key Positives (1 per key)
    for k_idx, k in enumerate(SORTED_17_KEYS):
        # Pick 6th instance of the class
        item = pos_by_class[k][5]
        case_counter += 1
        cid = f"synth_ctrl_wrong_{case_counter:03d}"
        inst = item["instance"]
        wrong_key = SORTED_17_KEYS[(k_idx + 1) % len(SORTED_17_KEYS)]
        synthetic_cases.append({
            "case_id": cid,
            "layer": "SYNTHETIC_CONTROLLED",
            "case_type": "WRONG_KEY_PROPOSAL",
            "source_id": item["sample_id"],
            "image_path": str(synth_img_dir / f"{item['sample_id']}.jpg"),
            "proposal_id": f"syn_wrong_{k}_{k_idx+1:02d}",
            "proposed_visual_candidate_key": wrong_key,
            "ground_truth_visual_candidate_key": k,
            "bbox_xyxy": inst["bbox_xyxy"],
            "is_negative": False,
            "is_wrong_key": True
        })

    # 20 Hard Negatives (4 per family across 5 families)
    hn_families = [
        "generic_branching_form",
        "isolated_lozenge_pattern",
        "octagonal_radial_variant",
        "radial_ornament_nonrosette",
        "radial_polygon_nonstar"
    ]
    family_proposed_key_map = {
        "generic_branching_form": "tree_like",
        "isolated_lozenge_pattern": "lozenge_like",
        "octagonal_radial_variant": "octagonal_form",
        "radial_ornament_nonrosette": "rosette_like",
        "radial_polygon_nonstar": "star_like"
    }

    for fam in sorted(hn_families):
        hns = hn_by_family[fam][:4]
        for idx, item in enumerate(hns):
            case_counter += 1
            cid = f"synth_ctrl_hn_{case_counter:03d}"
            hn = item["hn"]
            prop_key = family_proposed_key_map.get(fam, "unmapped_visual_motif")
            synthetic_cases.append({
                "case_id": cid,
                "layer": "SYNTHETIC_CONTROLLED",
                "case_type": "HARD_NEGATIVE",
                "source_id": item["sample_id"],
                "image_path": str(synth_img_dir / f"{item['sample_id']}.jpg"),
                "proposal_id": f"syn_hn_{fam}_{idx+1:02d}",
                "proposed_visual_candidate_key": prop_key,
                "ground_truth_visual_candidate_key": None,
                "hard_negative_family": fam,
                "bbox_xyxy": hn["bbox_xyxy"],
                "is_negative": True,
                "is_wrong_key": False
            })

    # 6 Background Negatives
    for idx, sid in enumerate(empty_samples[:6]):
        case_counter += 1
        cid = f"synth_ctrl_bg_{case_counter:03d}"
        prop_key = SORTED_17_KEYS[idx % len(SORTED_17_KEYS)]
        synthetic_cases.append({
            "case_id": cid,
            "layer": "SYNTHETIC_CONTROLLED",
            "case_type": "BACKGROUND_FALSE_POSITIVE",
            "source_id": sid,
            "image_path": str(synth_img_dir / f"{sid}.jpg"),
            "proposal_id": f"syn_bg_{idx+1:02d}",
            "proposed_visual_candidate_key": prop_key,
            "ground_truth_visual_candidate_key": None,
            "bbox_xyxy": [120.0, 120.0, 520.0, 520.0],
            "is_negative": True,
            "is_wrong_key": False
        })

    assert len(synthetic_cases) == 128, f"Expected 128 synthetic cases, got {len(synthetic_cases)}"

    # 2. LAYER B: REAL_GT_CONTROLLED (109 cases)
    real_dir = ROOT_DIR / "data/datasets/real-motif-benchmark-v1"
    real_annots = json.load(open(real_dir / "annotations.json", encoding="utf-8"))["data"]

    real_gt_cases = []
    real_case_counter = 0

    # Collect all GT instances
    real_gt_by_class = defaultdict(list)
    for img_entry in real_annots:
        img_fn = img_entry["filename"]
        for inst in img_entry["instances"]:
            k = id_to_class[inst["category_id"]]
            real_gt_by_class[k].append({
                "image_filename": img_fn,
                "instance": inst,
                "visual_key": k
            })

    # 92 Correct Proposals
    for img_entry in real_annots:
        img_fn = img_entry["filename"]
        img_p = str(real_dir / "images" / img_fn)
        for inst in img_entry["instances"]:
            real_case_counter += 1
            cid = f"real_gt_pos_{real_case_counter:03d}"
            k = id_to_class[inst["category_id"]]
            real_gt_cases.append({
                "case_id": cid,
                "layer": "REAL_GT_CONTROLLED",
                "case_type": "CORRECT_PROPOSAL",
                "source_id": img_fn,
                "image_path": img_p,
                "proposal_id": f"real_pos_{inst['instance_id']}",
                "proposed_visual_candidate_key": k,
                "ground_truth_visual_candidate_key": k,
                "bbox_xyxy": inst["bbox_xyxy"],
                "is_negative": False,
                "is_wrong_key": False
            })

    # 17 Wrong-Key Proposals (1 per class from real GT)
    for k_idx, k in enumerate(SORTED_17_KEYS):
        first_item = real_gt_by_class[k][0]
        real_case_counter += 1
        cid = f"real_gt_wrong_{real_case_counter:03d}"
        inst = first_item["instance"]
        wrong_key = SORTED_17_KEYS[(k_idx + 1) % len(SORTED_17_KEYS)]
        real_gt_cases.append({
            "case_id": cid,
            "layer": "REAL_GT_CONTROLLED",
            "case_type": "WRONG_KEY_PROPOSAL",
            "source_id": first_item["image_filename"],
            "image_path": str(real_dir / "images" / first_item["image_filename"]),
            "proposal_id": f"real_wrong_{inst['instance_id']}",
            "proposed_visual_candidate_key": wrong_key,
            "ground_truth_visual_candidate_key": k,
            "bbox_xyxy": inst["bbox_xyxy"],
            "is_negative": False,
            "is_wrong_key": True
        })

    assert len(real_gt_cases) == 109, f"Expected 109 real GT cases, got {len(real_gt_cases)}"

    # 3. LAYER C: REAL_DETECTOR_PROPOSALS (Detect & OBB)
    detect_model = YOLO(str(ROOT_DIR / "artifacts/v2-09b/models/yolo11n_detect_seed42/weights/best.pt"))
    obb_model = YOLO(str(ROOT_DIR / "artifacts/v2-09b/models/yolo11n_obb_seed42/weights/best.pt"))

    detect_proposals_cases = []
    obb_proposals_cases = []

    for img_entry in real_annots:
        img_fn = img_entry["filename"]
        img_p = str(real_dir / "images" / img_fn)

        # Detect
        res_d = detect_model.predict(img_p, conf=0.25, verbose=False)[0]
        if hasattr(res_d, "boxes") and res_d.boxes is not None:
            for b_idx in range(len(res_d.boxes)):
                cls_id = int(res_d.boxes.cls[b_idx].item())
                conf = float(res_d.boxes.conf[b_idx].item())
                xyxy = res_d.boxes.xyxy[b_idx].tolist()
                k = id_to_class[cls_id]
                pid = f"det_prop_{len(detect_proposals_cases)+1:03d}"
                detect_proposals_cases.append({
                    "case_id": f"real_det_prop_{len(detect_proposals_cases)+1:03d}",
                    "layer": "REAL_DETECTOR_DETECT",
                    "case_type": "DETECTOR_PROPOSAL",
                    "source_id": img_fn,
                    "image_path": img_p,
                    "proposal_id": pid,
                    "proposed_visual_candidate_key": k,
                    "bbox_xyxy": xyxy,
                    "confidence": conf,
                    "class_id": cls_id,
                    "model_family": "YOLO11n_Detect"
                })

        # OBB
        res_o = obb_model.predict(img_p, conf=0.25, verbose=False)[0]
        if hasattr(res_o, "obb") and res_o.obb is not None:
            for b_idx in range(len(res_o.obb)):
                cls_id = int(res_o.obb.cls[b_idx].item())
                conf = float(res_o.obb.conf[b_idx].item())
                xyxy = res_o.obb.xyxy[b_idx].tolist()
                k = id_to_class[cls_id]
                pid = f"obb_prop_{len(obb_proposals_cases)+1:03d}"
                obb_proposals_cases.append({
                    "case_id": f"real_obb_prop_{len(obb_proposals_cases)+1:03d}",
                    "layer": "REAL_DETECTOR_OBB",
                    "case_type": "DETECTOR_PROPOSAL",
                    "source_id": img_fn,
                    "image_path": img_p,
                    "proposal_id": pid,
                    "proposed_visual_candidate_key": k,
                    "bbox_xyxy": xyxy,
                    "confidence": conf,
                    "class_id": cls_id,
                    "model_family": "YOLO11n_OBB"
                })

    del detect_model
    del obb_model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    manifests = {
        "synthetic_controlled": {
            "cases": synthetic_cases,
            "count": len(synthetic_cases),
            "manifest_hash": hashlib.sha256(json.dumps(synthetic_cases, sort_keys=True).encode("utf-8")).hexdigest()
        },
        "real_gt_controlled": {
            "cases": real_gt_cases,
            "count": len(real_gt_cases),
            "manifest_hash": hashlib.sha256(json.dumps(real_gt_cases, sort_keys=True).encode("utf-8")).hexdigest()
        },
        "real_detector_detect": {
            "cases": detect_proposals_cases,
            "count": len(detect_proposals_cases),
            "manifest_hash": hashlib.sha256(json.dumps(detect_proposals_cases, sort_keys=True).encode("utf-8")).hexdigest()
        },
        "real_detector_obb": {
            "cases": obb_proposals_cases,
            "count": len(obb_proposals_cases),
            "manifest_hash": hashlib.sha256(json.dumps(obb_proposals_cases, sort_keys=True).encode("utf-8")).hexdigest()
        }
    }

    manifest_output_path = ROOT_DIR / "data/validation/v2-09c/benchmark-case-manifests.json"
    manifest_output_path.write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    print(f"Case manifests saved to {manifest_output_path}")
    print(f"Counts: Synthetic={len(synthetic_cases)}, Real GT={len(real_gt_cases)}, Detect={len(detect_proposals_cases)}, OBB={len(obb_proposals_cases)}")
    return manifests


def evaluate_model_on_cases(
    candidate_id: str,
    adapter: Any,
    manifests: Dict[str, Any],
    materializer: VisualVerifierPromptMaterializer,
    validator: VisualVerificationSemanticValidator,
    audit_record: Dict[str, Any]
) -> Dict[str, Any]:
    print(f"\n============================================================")
    print(f"Evaluating Candidate {candidate_id} across all frozen layers")
    print(f"============================================================")

    all_layer_cases = []
    for layer_name in ["synthetic_controlled", "real_gt_controlled", "real_detector_detect", "real_detector_obb"]:
        for c in manifests[layer_name]["cases"]:
            all_layer_cases.append((layer_name, c))

    case_results = []
    latencies = []
    generated_tokens_list = []

    first_real_evaluated_at = None

    t0_benchmark = time.perf_counter()

    for idx, (layer_name, c) in enumerate(all_layer_cases):
        # Check first real evaluation timestamp boundary
        if layer_name in ["real_gt_controlled", "real_detector_detect", "real_detector_obb"] and first_real_evaluated_at is None:
            first_real_evaluated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if audit_record.get("real_test_opened_at") is None:
                audit_record["real_test_opened_at"] = first_real_evaluated_at
                audit_record["real_test_first_evaluated_model"] = candidate_id
            print(f"[{candidate_id}] REAL_TEST boundary opened at {first_real_evaluated_at}")

        img_path = Path(c["image_path"])
        img = Image.open(img_path)
        canvas, png_hash = compose_verifier_input(
            img,
            c["bbox_xyxy"],
            c["proposal_id"],
            c["proposed_visual_candidate_key"]
        )

        canonical_msg = materializer.materialize(
            c["proposal_id"],
            c["proposed_visual_candidate_key"]
        )

        input_record = VerifierRuntimeInputRecord(
            run_id=audit_record["benchmark_run_id"],
            candidate_id=candidate_id,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proposal_id=c["proposal_id"],
            proposed_visual_candidate_key=c["proposed_visual_candidate_key"],
            prompt_sha256=FROZEN_PROMPT_HASH,
            materialized_prompt_sha256=hashlib.sha256(canonical_msg.materialized_prompt_text.encode("utf-8")).hexdigest(),
            canonical_semantic_payload_hash=canonical_msg.compute_canonical_hash(),
            png_sha256=png_hash,
            generation_policy_sha256=FROZEN_GENERATION_POLICY_HASH,
            adapter_id=f"{candidate_id}-v1.0.0",
            model_revision=FROZEN_CANDIDATE_SNAPSHOTS[candidate_id][:8],
            model_snapshot_sha256=FROZEN_CANDIDATE_SNAPSHOTS[candidate_id]
        )

        # Run inference
        inf_res = adapter.verify_case(
            image=canvas,
            canonical_message=canonical_msg,
            input_record=input_record
        )

        # Validate
        val_res = validator.validate(
            verifier_input={
                "proposal_id": c["proposal_id"],
                "proposed_visual_candidate_key": c["proposed_visual_candidate_key"]
            },
            raw_output_text=inf_res["raw_output"]
        )

        # Classify decision
        decision = val_res["decision"]
        verified_key = val_res["verified_visual_candidate_key"]
        schema_valid = val_res["schema_valid"]
        semantic_valid = val_res["semantic_valid"]

        if not (schema_valid and semantic_valid):
            classification = "INVALID_OUTPUT"
        else:
            classification = decision  # "ACCEPT", "REJECT", or "ABSTAIN"

        latencies.append(inf_res["inference_seconds"])
        generated_tokens_list.append(inf_res["generated_tokens"])

        case_results.append({
            "case_id": c["case_id"],
            "layer": layer_name,
            "case_type": c["case_type"],
            "source_id": c["source_id"],
            "proposal_id": c["proposal_id"],
            "proposed_visual_candidate_key": c["proposed_visual_candidate_key"],
            "ground_truth_key": c.get("ground_truth_visual_candidate_key"),
            "is_negative": c.get("is_negative", False),
            "is_wrong_key": c.get("is_wrong_key", False),
            "hard_negative_family": c.get("hard_negative_family"),
            "schema_valid": schema_valid,
            "semantic_valid": semantic_valid,
            "classification": classification,
            "raw_decision": decision,
            "verified_key": verified_key,
            "raw_output": inf_res["raw_output"],
            "raw_output_sha256": inf_res["raw_output_sha256"],
            "latency_seconds": inf_res["inference_seconds"],
            "generated_tokens": inf_res["generated_tokens"],
            "token_sequence_sha256": inf_res["token_sequence_sha256"],
            "png_sha256": png_hash,
            "canonical_payload_hash": inf_res["canonical_semantic_payload_hash"]
        })

        if (idx + 1) % 50 == 0 or (idx + 1) == len(all_layer_cases):
            print(f"[{candidate_id}] Completed {idx + 1}/{len(all_layer_cases)} cases...")

    wall_clock_dur = round(time.perf_counter() - t0_benchmark, 2)
    peak_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
    peak_res = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

    return {
        "candidate_id": candidate_id,
        "first_real_evaluated_at": first_real_evaluated_at,
        "wall_clock_seconds": wall_clock_dur,
        "peak_allocated_gib": peak_alloc,
        "peak_reserved_gib": peak_res,
        "mean_latency_seconds": round(float(np.mean(latencies)), 3),
        "median_latency_seconds": round(float(np.median(latencies)), 3),
        "p95_latency_seconds": round(float(np.percentile(latencies, 95)), 3),
        "mean_generated_tokens": round(float(np.mean(generated_tokens_list)), 1),
        "p95_generated_tokens": round(float(np.percentile(generated_tokens_list, 95)), 1),
        "total_cases_evaluated": len(case_results),
        "cases": case_results
    }


def compute_layer_metrics(case_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_cases = len(case_results)
    if total_cases == 0:
        return {}

    schema_valid_count = sum(1 for c in case_results if c["schema_valid"])
    semantic_valid_count = sum(1 for c in case_results if c["semantic_valid"])
    schema_valid_rate = round(schema_valid_count / total_cases, 4)
    semantic_valid_rate = round(semantic_valid_count / total_cases, 4)

    # Decisions
    valid_decisions = [c for c in case_results if c["schema_valid"] and c["semantic_valid"]]
    non_abstained = [c for c in valid_decisions if c["classification"] in ["ACCEPT", "REJECT"]]
    abstained_count = sum(1 for c in case_results if c["classification"] == "ABSTAIN")
    invalid_count = sum(1 for c in case_results if c["classification"] == "INVALID_OUTPUT")

    coverage = round(len(non_abstained) / total_cases, 4)

    # Selective Accuracy & Correct Outcomes
    correct_outcomes = 0
    for c in non_abstained:
        ctype = c["case_type"]
        dec = c["classification"]
        ver_key = c["verified_key"]
        gt_key = c["ground_truth_key"]

        if ctype == "CORRECT_PROPOSAL":
            if dec == "ACCEPT" and ver_key == gt_key:
                correct_outcomes += 1
        elif ctype == "WRONG_KEY_PROPOSAL":
            if dec == "ACCEPT" and ver_key == gt_key:
                correct_outcomes += 1
        elif ctype in ["HARD_NEGATIVE", "BACKGROUND_FALSE_POSITIVE"]:
            if dec == "REJECT":
                correct_outcomes += 1

    selective_accuracy = round(correct_outcomes / len(non_abstained), 4) if len(non_abstained) > 0 else "NOT_DEFINED"

    # Correct Key Accuracy on Accepted Positives
    accepted_positives = [c for c in valid_decisions if c["case_type"] in ["CORRECT_PROPOSAL", "WRONG_KEY_PROPOSAL"] and c["classification"] == "ACCEPT"]
    correct_key_positives = [c for c in accepted_positives if c["verified_key"] == c["ground_truth_key"]]
    correct_key_acc = round(len(correct_key_positives) / len(accepted_positives), 4) if len(accepted_positives) > 0 else "NOT_DEFINED"

    # False Accept Rate on Negatives
    negative_cases = [c for c in case_results if c.get("is_negative")]
    false_accepts = sum(1 for c in negative_cases if c["classification"] == "ACCEPT")
    false_accept_rate = round(false_accepts / len(negative_cases), 4) if len(negative_cases) > 0 else "NOT_DEFINED"

    # False Reject Rate on Positives
    positive_cases = [c for c in case_results if not c.get("is_negative")]
    false_rejects = sum(1 for c in positive_cases if c["classification"] == "REJECT")
    false_reject_rate = round(false_rejects / len(positive_cases), 4) if len(positive_cases) > 0 else "NOT_DEFINED"

    # Hard Negative Rejection Rate
    hn_cases = [c for c in case_results if c["case_type"] == "HARD_NEGATIVE"]
    hn_rejections = sum(1 for c in hn_cases if c["classification"] == "REJECT")
    hn_rejection_rate = round(hn_rejections / len(hn_cases), 4) if len(hn_cases) > 0 else "NOT_DEFINED"

    # Per-family Hard Negative Breakdown
    hn_family_metrics = {}
    for fam in [
        "generic_branching_form",
        "isolated_lozenge_pattern",
        "octagonal_radial_variant",
        "radial_ornament_nonrosette",
        "radial_polygon_nonstar"
    ]:
        fam_cases = [c for c in hn_cases if c.get("hard_negative_family") == fam]
        if fam_cases:
            f_accept = sum(1 for c in fam_cases if c["classification"] == "ACCEPT")
            f_reject = sum(1 for c in fam_cases if c["classification"] == "REJECT")
            f_abstain = sum(1 for c in fam_cases if c["classification"] == "ABSTAIN")
            f_invalid = sum(1 for c in fam_cases if c["classification"] == "INVALID_OUTPUT")
            f_fa_rate = round(f_accept / len(fam_cases), 4)
            accepted_keys = [c["verified_key"] for c in fam_cases if c["classification"] == "ACCEPT" and c["verified_key"]]
            hn_family_metrics[fam] = {
                "cases": len(fam_cases),
                "ACCEPT": f_accept,
                "REJECT": f_reject,
                "ABSTAIN": f_abstain,
                "INVALID_OUTPUT": f_invalid,
                "false_accept_rate": f_fa_rate,
                "accepted_key_distribution": dict(Counter(accepted_keys))
            }

    # Correction Metrics (on cases where proposal was wrong-key positive)
    wrong_key_cases = [c for c in case_results if c["case_type"] == "WRONG_KEY_PROPOSAL"]
    correction_attempts = [c for c in wrong_key_cases if c["classification"] == "ACCEPT" and c["verified_key"] != c["proposed_visual_candidate_key"]]
    correct_corrections = sum(1 for c in correction_attempts if c["verified_key"] == c["ground_truth_key"])
    incorrect_corrections = len(correction_attempts) - correct_corrections
    correction_accuracy = round(correct_corrections / len(correction_attempts), 4) if len(correction_attempts) > 0 else "NOT_DEFINED"

    return {
        "total_cases": total_cases,
        "schema_valid_count": schema_valid_count,
        "schema_valid_rate": schema_valid_rate,
        "semantic_valid_count": semantic_valid_count,
        "semantic_valid_rate": semantic_valid_rate,
        "coverage": coverage,
        "selective_accuracy": selective_accuracy,
        "correct_key_accuracy": correct_key_acc,
        "false_accept_rate": false_accept_rate,
        "false_reject_rate": false_reject_rate,
        "hard_negative_rejection_rate": hn_rejection_rate,
        "per_family_hard_negatives": hn_family_metrics,
        "correction_metrics": {
            "attempts": len(correction_attempts),
            "correct": correct_corrections,
            "incorrect": incorrect_corrections,
            "accuracy": correction_accuracy
        },
        "decisions_breakdown": {
            "ACCEPT": sum(1 for c in case_results if c["classification"] == "ACCEPT"),
            "REJECT": sum(1 for c in case_results if c["classification"] == "REJECT"),
            "ABSTAIN": abstained_count,
            "INVALID_OUTPUT": invalid_count
        }
    }


def compute_detector_pipeline_metrics(
    proposals_cases: List[Dict[str, Any]],
    case_results: List[Dict[str, Any]],
    real_annots: List[Dict[str, Any]],
    id_to_class: Dict[int, str]
) -> Dict[str, Any]:
    # 1. Base detector operating point
    total_images = len(real_annots)
    total_gt = sum(len(a["instances"]) for a in real_annots)

    # Match detector baseline proposals to GT
    base_tp = 0
    base_fp = 0

    proposals_by_img = defaultdict(list)
    for p in proposals_cases:
        proposals_by_img[p["source_id"]].append(p)

    for img_entry in real_annots:
        img_fn = img_entry["filename"]
        gts = img_entry["instances"]
        preds = proposals_by_img.get(img_fn, [])

        gt_matched = [False] * len(gts)
        for p in preds:
            matched = False
            for g_idx, gt in enumerate(gts):
                if gt_matched[g_idx]:
                    continue
                gt_k = id_to_class[gt["category_id"]]
                if p["proposed_visual_candidate_key"] == gt_k:
                    iou = compute_box_iou(p["bbox_xyxy"], gt["bbox_xyxy"])
                    if iou >= 0.50:
                        gt_matched[g_idx] = True
                        matched = True
                        base_tp += 1
                        break
            if not matched:
                base_fp += 1

    base_fn = total_gt - base_tp
    base_prec = round(base_tp / (base_tp + base_fp), 4) if (base_tp + base_fp) > 0 else 0.0
    base_rec = round(base_tp / total_gt, 4) if total_gt > 0 else 0.0
    base_fp_per_img = round(base_fp / total_images, 4)

    # 2. Verified detector pipeline operating point
    results_by_cid = {r["case_id"]: r for r in case_results}

    accepted_proposals = []
    accepted_count = 0
    rejected_count = 0
    abstained_count = 0
    invalid_count = 0

    for p in proposals_cases:
        r = results_by_cid.get(p["case_id"])
        if r is None:
            continue
        cls_decision = r["classification"]
        if cls_decision == "ACCEPT":
            accepted_count += 1
            # Use verified key
            verified_k = r["verified_key"] if r["verified_key"] else p["proposed_visual_candidate_key"]
            p_verified = dict(p)
            p_verified["effective_visual_key"] = verified_k
            accepted_proposals.append(p_verified)
        elif cls_decision == "REJECT":
            rejected_count += 1
        elif cls_decision == "ABSTAIN":
            abstained_count += 1
        else:
            invalid_count += 1

    ver_tp = 0
    ver_fp = 0
    ver_proposals_by_img = defaultdict(list)
    for p in accepted_proposals:
        ver_proposals_by_img[p["source_id"]].append(p)

    for img_entry in real_annots:
        img_fn = img_entry["filename"]
        gts = img_entry["instances"]
        preds = ver_proposals_by_img.get(img_fn, [])

        gt_matched = [False] * len(gts)
        for p in preds:
            matched = False
            for g_idx, gt in enumerate(gts):
                if gt_matched[g_idx]:
                    continue
                gt_k = id_to_class[gt["category_id"]]
                if p["effective_visual_key"] == gt_k:
                    iou = compute_box_iou(p["bbox_xyxy"], gt["bbox_xyxy"])
                    if iou >= 0.50:
                        gt_matched[g_idx] = True
                        matched = True
                        ver_tp += 1
                        break
            if not matched:
                ver_fp += 1

    ver_fn = total_gt - ver_tp
    ver_prec = round(ver_tp / (ver_tp + ver_fp), 4) if (ver_tp + ver_fp) > 0 else 0.0
    ver_rec = round(ver_tp / total_gt, 4) if total_gt > 0 else 0.0
    ver_fp_per_img = round(ver_fp / total_images, 4)

    precision_lift = round(ver_prec - base_prec, 4)
    recall_cost = round(base_rec - ver_rec, 4)
    fp_change = round(ver_fp_per_img - base_fp_per_img, 4)

    return {
        "detector_baseline": {
            "proposals": len(proposals_cases),
            "tp": base_tp,
            "fp": base_fp,
            "fn": base_fn,
            "precision": base_prec,
            "recall": base_rec,
            "fp_per_image": base_fp_per_img
        },
        "verified_pipeline": {
            "accepted_proposals": len(accepted_proposals),
            "tp": ver_tp,
            "fp": ver_fp,
            "fn": ver_fn,
            "precision": ver_prec,
            "recall": ver_rec,
            "fp_per_image": ver_fp_per_img
        },
        "precision_lift": precision_lift,
        "recall_cost": recall_cost,
        "fp_per_image_change": fp_change,
        "fractions": {
            "accepted": accepted_count,
            "rejected": rejected_count,
            "abstained": abstained_count,
            "invalid_output": invalid_count
        }
    }


def main():
    print("=" * 60)
    print("V2-09C.2 — FROZEN SMALL-VLM BENCHMARK EXECUTION")
    print("=" * 60)

    # 1. Pre-Run Freeze Verification
    freeze_data = verify_freeze_state()

    # 2. Benchmark Run ID & First-Look Audit Record
    run_id = f"v2-09c-2-{int(time.time())}"
    print(f"Benchmark Run ID: {run_id}")

    audit_record = {
        "benchmark_phase": "V2-09C.2",
        "phase_name": "Frozen Small-VLM Benchmark Execution",
        "benchmark_run_id": run_id,
        "pre_run_freeze_verification": "PASS",
        "config_hash": hashlib.sha256(json.dumps(freeze_data, sort_keys=True).encode("utf-8")).hexdigest(),
        "prompt_template_sha256": FROZEN_PROMPT_HASH,
        "schema_hash": FROZEN_SCHEMA_HASH,
        "compositor_hash": FROZEN_COMPOSITOR_HASH,
        "generation_policy_sha256": FROZEN_GENERATION_POLICY_HASH,
        "frozen_17_keys_hash": FROZEN_17_KEYS_HASH,
        "proposal_threshold": 0.25,
        "real_test_opened_at": None,
        "real_test_first_evaluated_model": None,
        "candidate_first_look_timestamps": {},
        "post_open_modifications": "NONE"
    }

    # 3. Materialize Case Manifests
    manifests = build_case_manifests()
    audit_record["manifest_hashes"] = {
        k: v["manifest_hash"] for k, v in manifests.items()
    }

    materializer = VisualVerifierPromptMaterializer()
    validator = VisualVerificationSemanticValidator()

    models_dir = ROOT_DIR / "artifacts/v2-09c/models"
    eligible_candidates = [
        ("C1", "Qwen3-VL-2B-Instruct", Qwen3VLAdapter("C1", models_dir / "C1")),
        ("C2", "SmolVLM2-2.2B-Instruct", SmolVLM2Adapter("C2", models_dir / "C2")),
        ("C3", "Qwen2-VL-2B-Instruct", Qwen2VLAdapter("C3", models_dir / "C3")),
    ]

    all_candidate_results = {}

    real_annots = json.load(open(ROOT_DIR / "data/datasets/real-motif-benchmark-v1/annotations.json", encoding="utf-8"))["data"]
    cm = load_class_map()
    id_to_class = {v: k for k, v in cm.items()}

    total_real_vlm_calls = 0

    # 4. Sequential Model Execution
    for cand_id, cand_name, adapter in eligible_candidates:
        print(f"\n--- Loading Candidate {cand_id}: {cand_name} ---")
        load_telemetry = adapter.load()
        print(f"[{cand_id}] Loaded in {load_telemetry['load_seconds']}s, peak memory {load_telemetry['peak_allocated_gib']} GiB")

        raw_eval_result = evaluate_model_on_cases(
            candidate_id=cand_id,
            adapter=adapter,
            manifests=manifests,
            materializer=materializer,
            validator=validator,
            audit_record=audit_record
        )

        audit_record["candidate_first_look_timestamps"][cand_id] = raw_eval_result["first_real_evaluated_at"]

        # Group cases by layer
        layer_cases_map = defaultdict(list)
        for c in raw_eval_result["cases"]:
            layer_cases_map[c["layer"]].append(c)

        # Count real calls
        real_calls_cand = len(layer_cases_map["real_gt_controlled"]) + len(layer_cases_map["real_detector_detect"]) + len(layer_cases_map["real_detector_obb"])
        total_real_vlm_calls += real_calls_cand

        # Compute metrics per layer
        synth_metrics = compute_layer_metrics(layer_cases_map["synthetic_controlled"])
        real_gt_metrics = compute_layer_metrics(layer_cases_map["real_gt_controlled"])

        detect_pipeline_metrics = compute_detector_pipeline_metrics(
            manifests["real_detector_detect"]["cases"],
            layer_cases_map["real_detector_detect"],
            real_annots,
            id_to_class
        )

        obb_pipeline_metrics = compute_detector_pipeline_metrics(
            manifests["real_detector_obb"]["cases"],
            layer_cases_map["real_detector_obb"],
            real_annots,
            id_to_class
        )

        all_candidate_results[cand_id] = {
            "candidate_id": cand_id,
            "candidate_name": cand_name,
            "snapshot_hash": FROZEN_CANDIDATE_SNAPSHOTS[cand_id],
            "load_telemetry": load_telemetry,
            "resource_telemetry": {
                "wall_clock_seconds": raw_eval_result["wall_clock_seconds"],
                "peak_allocated_gib": raw_eval_result["peak_allocated_gib"],
                "peak_reserved_gib": raw_eval_result["peak_reserved_gib"],
                "mean_latency_seconds": raw_eval_result["mean_latency_seconds"],
                "median_latency_seconds": raw_eval_result["median_latency_seconds"],
                "p95_latency_seconds": raw_eval_result["p95_latency_seconds"],
                "mean_generated_tokens": raw_eval_result["mean_generated_tokens"],
                "p95_generated_tokens": raw_eval_result["p95_generated_tokens"]
            },
            "synthetic_controlled": synth_metrics,
            "real_gt_controlled": real_gt_metrics,
            "detector_detect_pipeline": detect_pipeline_metrics,
            "detector_obb_pipeline": obb_pipeline_metrics,
            "raw_case_results_count": len(raw_eval_result["cases"])
        }

        # Unload
        unload_telemetry = adapter.unload()
        print(f"[{cand_id}] Unloaded. Residual memory: {unload_telemetry['post_unload_allocated_gib']} GiB")

    # Add R0 excluded entry
    all_candidate_results["R0"] = {
        "candidate_id": "R0",
        "candidate_name": "Qwen2.5-VL-3B-Instruct-AWQ",
        "snapshot_hash": FROZEN_CANDIDATE_SNAPSHOTS["R0"],
        "status": "NOT_EVALUATED_RUNTIME_EXCLUDED",
        "exclusion_reason": "RUNTIME_INCOMPATIBLE (AWQ INT4 compilation constraint on Py3.14 Windows)"
    }

    # 5. Write Final Result Artifacts
    audit_output_path = ROOT_DIR / "data/validation/v2-09c/real-test-first-look-audit.json"
    audit_output_path.write_text(json.dumps(audit_record, indent=2), encoding="utf-8")
    print(f"First-look audit saved to {audit_output_path}")

    final_benchmark_report = {
        "task": "V2-09C.2 — Frozen Small-VLM Visual Verifier Benchmark Execution",
        "status": "PASS_BENCHMARK_COMPLETE",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_run_id": run_id,
        "contract": {
            "verifier_version": "visual-verifier-v1.0.0",
            "prompt_template_version": "motif-visual-verifier-prompt-v1.0.0",
            "prompt_template_sha256": FROZEN_PROMPT_HASH,
            "schema_hash": FROZEN_SCHEMA_HASH,
            "compositor_hash": FROZEN_COMPOSITOR_HASH,
            "materializer_version": MATERIALIZER_VERSION,
            "canonical_message_contract": CANONICAL_MESSAGE_CONTRACT,
            "generation_policy_sha256": FROZEN_GENERATION_POLICY_HASH,
            "proposal_threshold": 0.25,
            "real_test_opened_at": audit_record["real_test_opened_at"],
            "real_test_vlm_call_count": total_real_vlm_calls
        },
        "manifest_summary": {
            "synthetic_controlled_cases": manifests["synthetic_controlled"]["count"],
            "real_gt_controlled_cases": manifests["real_gt_controlled"]["count"],
            "real_detector_detect_cases": manifests["real_detector_detect"]["count"],
            "real_detector_obb_cases": manifests["real_detector_obb"]["count"]
        },
        "candidates": all_candidate_results
    }

    result_json_path = ROOT_DIR / "data/validation/v2-09c/small-vlm-benchmark-result-v1.json"
    result_json_path.write_text(json.dumps(final_benchmark_report, indent=2), encoding="utf-8")
    print(f"Benchmark results saved to {result_json_path}")

    # Update real_test_vlm_call_count in freeze file
    freeze_data["real_test_vlm_call_count"] = total_real_vlm_calls
    (ROOT_DIR / "data/validation/v2-09c/visual-verifier-benchmark-freeze.json").write_text(
        json.dumps(freeze_data, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("V2-09C.2 BENCHMARK EXECUTION COMPLETE: PASS_BENCHMARK_COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
