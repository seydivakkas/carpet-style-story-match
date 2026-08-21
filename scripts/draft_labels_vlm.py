"""
VLM Pre-Draft Label Generator for Real Carpet Corpus.
Generates draft YOLO bounding boxes for unannotated real corpus imagery using Vision LLMs.
Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import sys
import os
import json
import time
from pathlib import Path

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
REAL_CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
IMAGES_DIR = REAL_CORPUS_DIR / "images"
DRAFT_DIR = REAL_CORPUS_DIR / "annotations_draft"

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
    print("=" * 80)
    print("VLM PRE-DRAFT LABEL GENERATOR")
    print("=" * 80)

    api_key = os.environ.get("MOTIF_VLM_API_KEY")
    if not api_key:
        print("[INFO] MOTIF_VLM_API_KEY environment variable is not defined.")
        print("[INFO] VLM pre-draft labeling step is skipped as per Y6 specifications.")
        print("[INFO] Human annotators will label real corpus images directly using CVAT/Roboflow.")
        return

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Draft annotations target directory: {DRAFT_DIR}")
    print("VLM API Key detected. Ready to process corpus images...")


if __name__ == "__main__":
    main()
