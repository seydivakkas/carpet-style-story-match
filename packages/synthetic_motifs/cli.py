"""
CLI Entrypoints for Synthetic Motif Dataset Generation and Validation.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import List, Dict, Any
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import Polygon
from packages.synthetic_motifs.registry import SyntheticMotifRegistry, VisualCandidateKey
from packages.synthetic_motifs.composer import CarpetComposer
from packages.synthetic_motifs.transforms import GeometricTransformer
from packages.synthetic_motifs.randomization import (
    PhotometricRandomizer,
    ImagingRandomizer,
    MaterialTextureRandomizer,
    OcclusionRandomizer,
)
from packages.synthetic_motifs.annotations import (
    SyntheticMotifInstanceGT,
    SyntheticCarpetSample,
)
from packages.synthetic_motifs.manifest import DatasetManifestGenerator
from packages.synthetic_motifs.exporters.canonical_json import CanonicalJsonExporter
from packages.synthetic_motifs.exporters.coco import CocoExporter
from packages.synthetic_motifs.exporters.yolo_detect import YoloDetectExporter
from packages.synthetic_motifs.exporters.yolo_obb import YoloObbExporter
from packages.synthetic_motifs.exporters.yolo_segment import YoloSegmentExporter
from packages.synthetic_motifs.validation import OracleValidator


def load_class_map() -> Dict[str, int]:
    class_map_path = Path("data/synthetic/visual-candidate-class-map-v1.json")
    if class_map_path.exists():
        with open(class_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {c["visual_candidate_key"]: c["class_id"] for c in data.get("classes", [])}
    # Fallback to sorted alphabetical
    keys = sorted([k.value for k in VisualCandidateKey])
    return {k: idx for idx, k in enumerate(keys)}


def generate_single_sample(
    composer: CarpetComposer,
    sample_id: str,
    seed: int,
    split: str,
    width: int = 640,
    height: int = 640,
    force_key: Any = None,
    is_negative: bool = False,
    hard_negative_mode: Optional[str] = None,
    apply_randomization: bool = True,
) -> Tuple[np.ndarray, SyntheticCarpetSample]:
    rng = np.random.RandomState(seed % (2**31 - 1))
    
    # 1. Base Composition
    canvas, instances, hard_negatives, scene_spec, scene_signature = composer.compose_scene(
        width=width,
        height=height,
        seed=seed,
        force_keys=[force_key] if force_key else None,
        is_negative=is_negative,
        hard_negative_mode=hard_negative_mode,
    )

    rand_profile = {}

    if apply_randomization and not is_negative and len(instances) > 0:
        # Extract polygons
        polys = [Polygon(inst.polygon) for inst in instances]

        # A. Geometric: Perspective warp (50% prob)
        if rng.uniform(0, 1) < 0.5:
            canvas, warped_polys, H, p_prov = GeometricTransformer.apply_perspective(
                canvas, polys, max_distortion=0.12, rng=rng
            )
            rand_profile["perspective"] = p_prov

            # Update instances with transformed geometry
            updated_instances = []
            for inst, w_poly in zip(instances, warped_polys):
                if w_poly is not None and w_poly.area > 32.0:
                    orig_poly = Polygon(inst.polygon)
                    vis_frac = float(min(1.0, w_poly.area / max(1.0, orig_poly.area)))
                    bbox = w_poly.get_bounding_box()
                    obb = w_poly.get_oriented_bounding_box()
                    
                    inst.polygon = w_poly.to_list()
                    inst.bbox_xyxy = bbox.to_xyxy()
                    inst.bbox_normalized = bbox.to_normalized(width, height)
                    inst.obb = obb.to_list()
                    inst.obb_normalized = obb.to_normalized(width, height)
                    inst.visible_fraction = vis_frac
                    inst.is_truncated = (vis_frac < 0.95)
                    inst.ignore = (vis_frac < 0.20)
                    inst.transform_provenance.update({"perspective": p_prov})
                    updated_instances.append(inst)
            instances = updated_instances

        # B. Material texture & fiber
        canvas, mat_prov = MaterialTextureRandomizer.apply(canvas, fiber_amplitude=0.05, wear_prob=0.5, rng=rng)
        rand_profile["material"] = mat_prov

        # C. Photometric alterations (invariance check: does NOT alter geometry)
        canvas, photo_prov = PhotometricRandomizer.apply(canvas, rng=rng)
        rand_profile["photometric"] = photo_prov

        # D. Imaging noise & JPEG
        canvas, img_prov = ImagingRandomizer.apply(canvas, blur_prob=0.3, noise_prob=0.4, rng=rng)
        rand_profile["imaging"] = img_prov

    sample = SyntheticCarpetSample(
        sample_id=sample_id,
        seed=seed,
        split=split,
        image_width=width,
        image_height=height,
        image_ref=f"images/{split}/{sample_id}.jpg",
        mask_ref=f"masks/{split}/{sample_id}_mask.png" if instances else None,
        scene_signature=scene_signature,
        scene_spec=scene_spec,
        randomization_profile=rand_profile,
        artifact_hashes={},
        instances=instances,
        hard_negatives=hard_negatives,
    )
    return canvas, sample


def run_generate_dataset(
    output_dir: Path,
    total_samples: int = 200,
    master_seed: int = 42,
    width: int = 640,
    height: int = 640,
    dry_run: bool = False,
) -> Dict[str, Any]:
    registry = SyntheticMotifRegistry()
    composer = CarpetComposer(registry)
    class_map = load_class_map()
    all_keys = registry.list_keys()

    master_rng = np.random.RandomState(master_seed)
    
    # Split allocations: 70% train, 15% val, 15% test
    n_train = int(total_samples * 0.70)
    n_val = int(total_samples * 0.15)
    n_test = total_samples - n_train - n_val

    splits = ["train"] * n_train + ["validation"] * n_val + ["test"] * n_test
    master_rng.shuffle(splits)

    if dry_run:
        print("=== DRY RUN SUMMARY ===")
        print(f"Total planned samples: {total_samples}")
        print(f"Splits: train={n_train}, validation={n_val}, test={n_test}")
        print(f"Supported classes ({len(all_keys)}): {[k.value for k in all_keys]}")
        print(f"Image dimensions: {width}x{height}")
        print(f"Estimated raw artifact size: ~{total_samples * 0.15:.2f} MB")
        return {
            "dry_run": True,
            "total_samples": total_samples,
            "split_counts": {"train": n_train, "validation": n_val, "test": n_test},
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    samples_dir = output_dir / "samples"
    yolo_dir = output_dir / "yolo"
    yolo_obb_dir = output_dir / "yolo_obb"
    yolo_seg_dir = output_dir / "yolo_segment"

    for s_name in ["train", "validation", "test"]:
        (images_dir / s_name).mkdir(parents=True, exist_ok=True)
        (yolo_dir / "labels" / s_name).mkdir(parents=True, exist_ok=True)
        (yolo_obb_dir / "labels" / s_name).mkdir(parents=True, exist_ok=True)
        (yolo_seg_dir / "labels" / s_name).mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    generated_samples: List[SyntheticCarpetSample] = []
    samples_by_split: Dict[str, List[SyntheticCarpetSample]] = {"train": [], "validation": [], "test": []}

    t0 = time.time()

    seen_sigs_by_split: Dict[str, set] = {"train": set(), "validation": set(), "test": set()}

    for i in range(total_samples):
        sample_id = f"syn_{i + 1:06d}"
        split_i = splits[i]

        # Allocation policy:
        # i % 20 == 9 -> Empty negative (0 targets, 0 hard negatives)
        # i % 20 == 19 -> Hard negative only (0 targets, >=1 hard negatives)
        # i % 10 in (2, 6) -> Mixed hard negative (targets + hard negatives)
        # otherwise -> Positive target sample

        is_neg = False
        hn_mode = None

        if i % 20 == 9:
            is_neg = True
            hn_mode = None
        elif i % 20 == 19:
            is_neg = True
            hn_mode = "HARD_NEGATIVE_ONLY"
        elif i % 10 in (2, 6):
            is_neg = False
            hn_mode = "MIXED_HARD_NEGATIVE"

        force_key = None if is_neg else all_keys[i % len(all_keys)]

        seed_attempt = int(master_rng.randint(1, 2**31 - 1))
        while True:
            canvas, sample = generate_single_sample(
                composer=composer,
                sample_id=sample_id,
                seed=seed_attempt,
                split=split_i,
                width=width,
                height=height,
                force_key=force_key,
                is_negative=is_neg,
                hard_negative_mode=hn_mode,
            )
            # Verify no cross-split leakage
            collides = False
            for other_s, other_sigs in seen_sigs_by_split.items():
                if other_s != split_i and sample.scene_signature in other_sigs:
                    collides = True
                    break
            if not collides:
                seen_sigs_by_split[split_i].add(sample.scene_signature)
                break
            seed_attempt = (seed_attempt + 10007) % (2**31 - 1)

        # Save JPEG image
        img_path = images_dir / split_i / f"{sample_id}.jpg"
        cv2.imwrite(str(img_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        
        # Calculate image sha256
        with open(img_path, "rb") as f:
            sample.artifact_hashes["image_sha256"] = hashlib.sha256(f.read()).hexdigest()

        # Save Canonical JSON
        sample_json_path = samples_dir / f"{sample_id}.json"
        CanonicalJsonExporter.export(sample, sample_json_path)

        # Save YOLO detect
        yolo_txt_path = yolo_dir / "labels" / split_i / f"{sample_id}.txt"
        YoloDetectExporter.export_sample(sample, class_map, yolo_txt_path)

        # Save YOLO OBB
        yolo_obb_txt_path = yolo_obb_dir / "labels" / split_i / f"{sample_id}.txt"
        YoloObbExporter.export_sample(sample, class_map, yolo_obb_txt_path)

        # Save YOLO segment
        yolo_seg_txt_path = yolo_seg_dir / "labels" / split_i / f"{sample_id}.txt"
        YoloSegmentExporter.export_sample(sample, class_map, yolo_seg_txt_path)

        generated_samples.append(sample)
        samples_by_split[split_i].append(sample)

    elapsed = time.time() - t0

    # Export COCO format for each split
    annotations_dir = output_dir / "annotations"
    annotations_dir.mkdir(parents=True, exist_ok=True)
    for s_name in ["train", "validation", "test"]:
        coco_path = annotations_dir / f"coco_{s_name}.json"
        CocoExporter.export(samples_by_split[s_name], class_map, coco_path, split_name=s_name)

    # Build and export Manifest
    manifest_data = DatasetManifestGenerator.generate_manifest(
        samples=generated_samples,
        master_seed=master_seed,
        annotation_formats=["canonical_json", "coco", "yolo_detect", "yolo_obb", "yolo_segment"],
    )
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return {
        "total_samples": len(generated_samples),
        "split_counts": manifest_data["split_counts"],
        "class_counts": manifest_data["class_counts"],
        "negative_samples_count": manifest_data["negative_samples_count"],
        "empty_negative_sample_count": manifest_data.get("empty_negative_sample_count", 0),
        "hard_negative_sample_count": manifest_data.get("hard_negative_sample_count", 0),
        "mixed_hard_negative_sample_count": manifest_data.get("mixed_hard_negative_sample_count", 0),
        "hard_negative_instance_count": manifest_data.get("hard_negative_instance_count", 0),
        "elapsed_sec": round(elapsed, 2),
        "samples_per_sec": round(len(generated_samples) / max(elapsed, 0.001), 2),
        "manifest_path": str(manifest_path),
    }


def validate_dataset_folder(dataset_dir: Path) -> Dict[str, Any]:
    """Validates an existing dataset directory for integrity, bounds, oracle compliance, and zero hard-negative leakage."""
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    samples_dir = dataset_dir / "samples"
    images_dir = dataset_dir / "images"

    total_instances = 0
    total_hard_negatives = 0
    bbox_violations = 0
    obb_violations = 0
    polygon_violations = 0
    image_missing = 0
    positive_label_leak_count = 0

    seen_sigs = {}
    leakage_count = 0

    for s_entry in manifest.get("samples", []):
        sid = s_entry["sample_id"]
        split = s_entry["split"]
        sig = s_entry["scene_signature"]

        if sig in seen_sigs and seen_sigs[sig] != split:
            leakage_count += 1
        seen_sigs[sig] = split

        # Check sample json
        s_json_path = samples_dir / f"{sid}.json"
        if not s_json_path.exists():
            continue
        with open(s_json_path, "r", encoding="utf-8") as f:
            sample_obj = json.load(f)

        # Check image file
        img_path = images_dir / split / f"{sid}.jpg"
        if not img_path.exists():
            image_missing += 1

        w = float(sample_obj["image_width"])
        h = float(sample_obj["image_height"])

        inst_keys = set()
        for inst in sample_obj.get("instances", []):
            total_instances += 1
            inst_keys.add(inst["visual_candidate_key"])
            inst_keys.add(inst["instance_id"])

            # Check bbox bounds
            xmin, ymin, xmax, ymax = inst["bbox_xyxy"]
            if xmin < -2.0 or ymin < -2.0 or xmax > w + 2.0 or ymax > h + 2.0 or xmin >= xmax or ymin >= ymax:
                bbox_violations += 1

            # Check polygon
            poly_pts = inst["polygon"]
            if len(poly_pts) < 3:
                polygon_violations += 1
            else:
                poly = Polygon(poly_pts)
                if not OracleValidator.verify_obb_containment(poly, inst["obb"], margin=2.0):
                    obb_violations += 1

        # Check hard negative leakage into positive target instances
        for hn in sample_obj.get("hard_negatives", []):
            total_hard_negatives += 1
            hn_key = hn["hard_negative_key"]
            hn_id = hn["hard_negative_id"]
            if hn_key in inst_keys or hn_id in inst_keys:
                positive_label_leak_count += 1

    status = "PASS" if (
        bbox_violations == 0
        and obb_violations == 0
        and leakage_count == 0
        and image_missing == 0
        and positive_label_leak_count == 0
    ) else "FAIL"

    return {
        "status": status,
        "total_samples": len(manifest.get("samples", [])),
        "total_instances": total_instances,
        "total_hard_negatives": total_hard_negatives,
        "bbox_violations": bbox_violations,
        "obb_violations": obb_violations,
        "polygon_violations": polygon_violations,
        "leakage_count": leakage_count,
        "positive_label_leak_count": positive_label_leak_count,
        "image_missing": image_missing,
    }


def main():
    parser = argparse.ArgumentParser(description="Synthetic Motif Dataset CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate
    gen_p = subparsers.add_parser("generate", help="Generate synthetic motif dataset")
    gen_p.add_argument("--output", type=str, default="data/synthetic/acceptance_samples", help="Output directory")
    gen_p.add_argument("--samples", type=int, default=200, help="Total samples to generate")
    gen_p.add_argument("--seed", type=int, default=42, help="Master random seed")
    gen_p.add_argument("--width", type=int, default=640, help="Image width")
    gen_p.add_argument("--height", type=int, default=640, help="Image height")
    gen_p.add_argument("--dry-run", action="store_true", help="Print planned execution without saving files")

    # Validate
    val_p = subparsers.add_parser("validate-dataset", help="Validate an existing synthetic dataset directory")
    val_p.add_argument("--dataset-path", type=str, required=True, help="Path to dataset directory")

    args = parser.parse_args()

    if args.command == "generate":
        res = run_generate_dataset(
            output_dir=Path(args.output),
            total_samples=args.samples,
            master_seed=args.seed,
            width=args.width,
            height=args.height,
            dry_run=args.dry_run,
        )
        print(json.dumps(res, indent=2))
    elif args.command == "validate-dataset":
        res = validate_dataset_folder(Path(args.dataset_path))
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
