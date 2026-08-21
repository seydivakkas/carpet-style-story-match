"""
Generates representative synthetic motif example crops for docs/labeling-guide-v1.md.
Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import sys
import os
import json
from pathlib import Path
import cv2
import numpy as np

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
EXAMPLES_DIR = ROOT_DIR / "docs" / "labeling-guide-v1-examples"
DATASET_DIR = ROOT_DIR / "artifacts" / "v2-10" / "dataset" / "yolo_detect"

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


def main():
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = DATASET_DIR / "images" / "train"
    labels_dir = DATASET_DIR / "labels" / "train"

    crops_per_class = {c: [] for c in CLASSES}

    label_files = sorted(list(labels_dir.glob("*.txt")))
    print(f"Scanning {len(label_files)} label files to extract 2 high-quality crops per class...")

    for lf in label_files:
        img_f = images_dir / (lf.stem + ".png")
        if not img_f.exists():
            img_f = images_dir / (lf.stem + ".jpg")
        if not img_f.exists():
            continue

        with open(lf, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Read image only if this file contains a class we still need
        needed_in_file = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                cid = int(parts[0])
                cname = CLASSES[cid]
                if len(crops_per_class[cname]) < 2:
                    needed_in_file.append((cid, cname, list(map(float, parts[1:5]))))

        if not needed_in_file:
            continue

        img = cv2.imread(str(img_f))
        if img is None:
            continue
        ih, iw = img.shape[:2]

        for cid, cname, (xc, yc, w, h) in needed_in_file:
            if len(crops_per_class[cname]) >= 2:
                continue

            x1 = int(max(0, (xc - w / 2) * iw - 8))
            y1 = int(max(0, (yc - h / 2) * ih - 8))
            x2 = int(min(iw, (xc + w / 2) * iw + 8))
            y2 = int(min(ih, (yc + h / 2) * ih + 8))

            crop = img[y1:y2, x1:x2]
            if crop.shape[0] < 20 or crop.shape[1] < 20:
                continue

            crop_idx = len(crops_per_class[cname]) + 1
            out_name = f"{cname}_example_{crop_idx}.png"
            out_path = EXAMPLES_DIR / out_name
            cv2.imwrite(str(out_path), crop)
            crops_per_class[cname].append(out_name)
            print(f"  Extracted {out_name} (size: {crop.shape[1]}x{crop.shape[0]})")

        if all(len(crops) >= 2 for crops in crops_per_class.values()):
            break

    print(f"\nSuccessfully extracted all 34 examples across 17 classes to: {EXAMPLES_DIR}")


if __name__ == "__main__":
    main()
