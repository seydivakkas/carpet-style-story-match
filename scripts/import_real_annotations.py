"""
Real Annotations Import and Verification Pipeline.
Validates Roboflow/CVAT YOLO exports, enforces zero holdout leakage, and stages real dataset for Y7 training.
Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import sys
import os
import json
import time
import shutil
import hashlib
import argparse
from pathlib import Path
import cv2

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
REAL_CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
CORPUS_IMAGES_DIR = REAL_CORPUS_DIR / "images"
CORPUS_ANNOTATIONS_DIR = REAL_CORPUS_DIR / "annotations"
STAGING_DIR = ROOT_DIR / "artifacts" / "v2-11" / "dataset" / "staging"

CLASSES = [
    "cloud_band_like",
    "comb_like",
    "hook_like",
    "horn_like",
    "human_figure_like_geometric",
    "lattice_like",
    "lotus_like",
    "lozenge_like",
    "medallion_like",
    "niche_like",
    "octagonal_form",
    "palmette_like",
    "rosette_like",
    "star_like",
    "tree_like",
    "unmapped_visual_motif",
    "vine_scroll_like",
]


def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_holdout_blacklist() -> set:
    blacklist = set()
    dirs_to_check = [
        ROOT_DIR / "data" / "datasets" / "real-motif-benchmark-v1" / "images",
        ROOT_DIR / "scratch" / "curation_images",
    ]
    for d in dirs_to_check:
        if d.exists():
            for f in d.glob("**/*"):
                if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    try:
                        blacklist.add(compute_file_sha256(f))
                    except Exception:
                        pass
    return blacklist


def validate_yolo_label_file(lbl_path: Path, num_classes: int = 17):
    """
    Validates a single YOLO format label file.
    Returns: (is_valid, boxes_list, warnings, errors)
    """
    warnings = []
    errors = []
    boxes = []

    if not lbl_path.exists():
        errors.append(f"Label file does not exist: {lbl_path}")
        return False, boxes, warnings, errors

    with open(lbl_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) == 0:
        warnings.append(f"Empty label file (0 bounding boxes): {lbl_path.name}")
        return True, boxes, warnings, errors

    for line_idx, line in enumerate(lines, 1):
        parts = line.split()
        if len(parts) < 5:
            errors.append(f"{lbl_path.name}:{line_idx} - Invalid format, expected >=5 tokens, got {len(parts)}")
            continue

        try:
            cid = int(parts[0])
            xc = float(parts[1])
            yc = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except ValueError as e:
            errors.append(f"{lbl_path.name}:{line_idx} - Value conversion error: {e}")
            continue

        if not (0 <= cid < num_classes):
            errors.append(f"{lbl_path.name}:{line_idx} - Class ID {cid} out of range [0, {num_classes-1}]")

        for val_name, val in [("x_center", xc), ("y_center", yc), ("width", w), ("height", h)]:
            if not (0.0 <= val <= 1.0):
                errors.append(f"{lbl_path.name}:{line_idx} - Coordinate {val_name}={val} out of bounds [0.0, 1.0]")

        if w <= 0.0 or h <= 0.0:
            errors.append(f"{lbl_path.name}:{line_idx} - Non-positive dimensions: w={w}, h={h}")

        boxes.append({"class_id": cid, "class_name": CLASSES[cid] if 0 <= cid < num_classes else "invalid", "bbox_norm": [xc, yc, w, h]})

    is_valid = len(errors) == 0
    return is_valid, boxes, warnings, errors


def import_and_stage_annotations(source_images_dir: Path, source_labels_dir: Path, staging_out_dir: Path, dry_run: bool = False):
    print("=" * 80)
    print("STARTING REAL ANNOTATIONS IMPORT & STAGING PIPELINE")
    print(f"Source Images: {source_images_dir}")
    print(f"Source Labels: {source_labels_dir}")
    print(f"Staging Out:   {staging_out_dir}")
    print("=" * 80)

    holdout_blacklist = load_holdout_blacklist()
    print(f"Holdout Blacklist: {len(holdout_blacklist)} holdout image SHA256 hashes loaded.")

    stage_images_dir = staging_out_dir / "images"
    stage_labels_dir = staging_out_dir / "labels"
    stage_images_dir.mkdir(parents=True, exist_ok=True)
    stage_labels_dir.mkdir(parents=True, exist_ok=True)

    label_files = sorted(list(source_labels_dir.glob("*.txt")))
    if not label_files:
        print("[WARNING] No label files found in source directory.")
        return False, {}

    print(f"Discovered {len(label_files)} annotation files to process.")

    total_boxes = 0
    class_counts = {c: 0 for c in CLASSES}
    valid_samples = []
    all_warnings = []
    all_errors = []
    holdout_leakage_detected = []

    for lf in label_files:
        stem = lf.stem
        # Check image existence
        img_candidates = [
            source_images_dir / f"{stem}.jpg",
            source_images_dir / f"{stem}.jpeg",
            source_images_dir / f"{stem}.png",
        ]
        img_path = next((p for p in img_candidates if p.exists()), None)
        if not img_path:
            all_errors.append(f"Image not found for label file: {lf.name}")
            continue

        # Holdout Blacklist Check
        img_sha = compute_file_sha256(img_path)
        if img_sha in holdout_blacklist:
            err_msg = f"[CRITICAL LEAKAGE] Image {img_path.name} (SHA: {img_sha}) matches holdout benchmark blacklist!"
            holdout_leakage_detected.append(err_msg)
            all_errors.append(err_msg)
            print(f"ERROR: {err_msg}")
            raise ValueError(err_msg)

        # Validate label file
        is_valid, boxes, warnings, errors = validate_yolo_label_file(lf, num_classes=len(CLASSES))
        all_warnings.extend(warnings)
        all_errors.extend(errors)

        if not is_valid:
            continue

        # Stage image and label
        dst_img = stage_images_dir / img_path.name
        dst_lbl = stage_labels_dir / lf.name

        shutil.copy2(img_path, dst_img)
        shutil.copy2(lf, dst_lbl)

        total_boxes += len(boxes)
        for b in boxes:
            class_counts[b["class_name"]] += 1

        valid_samples.append({
            "image_filename": img_path.name,
            "label_filename": lf.name,
            "sha256": img_sha,
            "box_count": len(boxes),
            "boxes": boxes,
        })

    # Write staging manifest draft
    manifest_data = {
        "staging_version": "v2-11-staging-v1.0.0",
        "dataset_name": "real_carpet_annotated_staging",
        "imported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_images_staged": len(valid_samples),
        "total_bounding_boxes": total_boxes,
        "class_distribution": class_counts,
        "holdout_leakage_checks_passed": len(holdout_leakage_detected) == 0,
        "holdout_blacklist_size": len(holdout_blacklist),
        "warnings_count": len(all_warnings),
        "errors_count": len(all_errors),
        "staged_samples": valid_samples,
    }

    manifest_file = staging_out_dir / "manifest_draft.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("IMPORT & STAGING SUMMARY")
    print(f"Images Successfully Staged: {len(valid_samples)} / {len(label_files)}")
    print(f"Total Bounding Boxes:      {total_boxes}")
    print(f"Holdout Leakage Count:     {len(holdout_leakage_detected)} (MUST BE 0)")
    print(f"Manifest Draft Written:    {manifest_file}")
    print("=" * 80)

    return len(all_errors) == 0, manifest_data


def run_dry_run_pipeline():
    """
    Creates temporary mock annotations on 4 real corpus images to verify import pipeline,
    verifies staging & manifest generation, and then cleans up temporary test inputs.
    """
    print("\n>>> EXECUTING DRY-RUN PIPELINE VERIFICATION <<<")
    corpus_imgs = sorted(list(CORPUS_IMAGES_DIR.glob("*.jpg")))[:4]
    if not corpus_imgs:
        print("[ERROR] No real corpus images available for dry-run.")
        return False

    temp_test_labels_dir = ROOT_DIR / "scratch" / "dry_run_labels"
    temp_test_labels_dir.mkdir(parents=True, exist_ok=True)

    # Create 4 valid sample annotations
    test_annotations = [
        [(8, 0.5, 0.5, 0.4, 0.4), (12, 0.2, 0.2, 0.1, 0.1)],  # medallion + rosette
        [(3, 0.3, 0.3, 0.15, 0.15), (7, 0.7, 0.7, 0.2, 0.2)], # horn + lozenge
        [(14, 0.5, 0.6, 0.25, 0.5)],                            # tree_like
        [(9, 0.5, 0.4, 0.35, 0.45), (16, 0.1, 0.5, 0.1, 0.8)], # niche + vine_scroll
    ]

    for img_path, boxes in zip(corpus_imgs, test_annotations):
        lbl_file = temp_test_labels_dir / (img_path.stem + ".txt")
        lines = [f"{b[0]} {b[1]} {b[2]} {b[3]} {b[4]}" for b in boxes]
        with open(lbl_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # Run staging import
    success, manifest = import_and_stage_annotations(
        source_images_dir=CORPUS_IMAGES_DIR,
        source_labels_dir=temp_test_labels_dir,
        staging_out_dir=STAGING_DIR,
        dry_run=True,
    )

    # Clean up temporary dry-run test directory
    shutil.rmtree(temp_test_labels_dir, ignore_errors=True)
    print("Dry-run temporary input labels cleaned up successfully.")
    return success


def parse_args():
    parser = argparse.ArgumentParser(description="Import and Stage Real Carpet Annotations")
    parser.add_argument("--images-dir", type=str, default=str(CORPUS_IMAGES_DIR), help="Source images directory")
    parser.add_argument("--labels-dir", type=str, default=str(CORPUS_ANNOTATIONS_DIR), help="Source YOLO labels directory")
    parser.add_argument("--staging-dir", type=str, default=str(STAGING_DIR), help="Staging output directory")
    parser.add_argument("--dry-run", action="store_true", help="Execute dry-run with temporary mock annotations")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.dry_run:
        success = run_dry_run_pipeline()
        sys.exit(0 if success else 1)

    labels_dir = Path(args.labels_dir)
    images_dir = Path(args.images_dir)
    staging_dir = Path(args.staging_dir)

    label_files = list(labels_dir.glob("*.txt")) if labels_dir.exists() else []
    if not label_files:
        print(f"[INFO] No real annotation files found in {labels_dir}. Running dry-run verification...")
        success = run_dry_run_pipeline()
    else:
        success, _ = import_and_stage_annotations(
            source_images_dir=images_dir,
            source_labels_dir=labels_dir,
            staging_out_dir=staging_dir,
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
