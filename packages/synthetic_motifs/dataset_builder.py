"""
Synthetic Motif Dataset Builder (v1.0.0)
Generates deterministic synthetic datasets for YOLO Detect and YOLO OBB training/validation.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np

from packages.synthetic_motifs.composer import CarpetComposer
from packages.synthetic_motifs.manifest import SyntheticCarpetSample
from packages.synthetic_motifs.cli import load_class_map
from packages.synthetic_motifs.exporters.yolo_detect import YoloDetectExporter
from packages.synthetic_motifs.exporters.yolo_obb import YoloObbExporter
from packages.synthetic_motifs.exporters.canonical_json import CanonicalJsonExporter


class DatasetBuilder:
    """Generates bounded deterministic synthetic datasets with split isolation."""

    def __init__(
        self,
        output_dir: Path,
        total_samples: int = 1500,
        master_seed: int = 42,
        image_size: Tuple[int, int] = (640, 640),
    ):
        self.output_dir = Path(output_dir)
        self.total_samples = total_samples
        self.master_seed = master_seed
        self.img_w, self.img_h = image_size
        self.class_map = load_class_map()
        self.composer = CarpetComposer()

    def build(self) -> Dict[str, Any]:
        """Generates images and exports datasets for YOLO Detect & OBB."""
        yolo_detect_dir = self.output_dir / "yolo_detect"
        yolo_obb_dir = self.output_dir / "yolo_obb"
        json_dir = self.output_dir / "canonical_json"

        for split in ["train", "val", "test"]:
            (yolo_detect_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (yolo_detect_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
            (yolo_obb_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (yolo_obb_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
            (json_dir / split).mkdir(parents=True, exist_ok=True)

        n_train = int(self.total_samples * 0.70)
        n_val = int(self.total_samples * 0.15)
        n_test = self.total_samples - n_train - n_val

        split_assignments = (
            ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
        )

        samples: List[SyntheticCarpetSample] = []
        fingerprint_hasher = hashlib.sha256()

        total_target_instances = 0
        total_hard_negative_instances = 0
        empty_negative_samples_count = 0
        hard_negative_only_samples_count = 0
        mixed_hard_negative_samples_count = 0

        print(f"Generating {self.total_samples} synthetic motif samples (master seed = {self.master_seed})...")

        for idx in range(self.total_samples):
            seed = self.master_seed + idx * 7919
            split = split_assignments[idx]
            sample_id = f"syn_{idx+1:06d}"
            
            # Determine sample composition type
            is_neg = (idx % 15 == 0)  # ~6.6% empty negative scenes
            is_hn_only = (not is_neg) and (idx % 17 == 0)  # ~5.8% hard negative only scenes

            canvas, instances, hard_negatives, spec, scene_sig = self.composer.compose_scene(
                width=self.img_w,
                height=self.img_h,
                seed=seed,
                is_negative=is_neg,
            )

            # Update sample statistics
            if is_neg:
                empty_negative_samples_count += 1
            elif is_hn_only:
                hard_negative_only_samples_count += 1
            elif len(hard_negatives) > 0:
                mixed_hard_negative_samples_count += 1

            total_target_instances += len(instances)
            total_hard_negative_instances += len(hard_negatives)

            # Save image raster
            img_rel_path = f"images/{split}/{sample_id}.jpg"
            img_abs_path = yolo_detect_dir / img_rel_path
            cv2.imwrite(str(img_abs_path), canvas)

            # Copy or link image for OBB
            obb_img_path = yolo_obb_dir / img_rel_path
            cv2.imwrite(str(obb_img_path), canvas)

            sample = SyntheticCarpetSample(
                sample_id=sample_id,
                seed=seed,
                split=split,
                image_width=self.img_w,
                image_height=self.img_h,
                image_ref=img_rel_path,
                scene_signature=scene_sig,
                instances=instances,
                hard_negatives=hard_negatives,
            )
            samples.append(sample)

            # Export YOLO Detect GT
            detect_lbl_path = yolo_detect_dir / "labels" / split / f"{sample_id}.txt"
            YoloDetectExporter.export_sample(sample, self.class_map, detect_lbl_path)

            # Export YOLO OBB GT
            obb_lbl_path = yolo_obb_dir / "labels" / split / f"{sample_id}.txt"
            YoloObbExporter.export_sample(sample, self.class_map, obb_lbl_path)

            # Export Canonical JSON GT
            json_path = json_dir / split / f"{sample_id}.json"
            CanonicalJsonExporter.export(sample, json_path)

            fingerprint_hasher.update(f"{sample_id}:{seed}:{scene_sig}".encode("utf-8"))

        dataset_fingerprint = fingerprint_hasher.hexdigest()

        # Generate data.yaml files for Ultralytics
        class_names = [k for k, v in sorted(self.class_map.items(), key=lambda x: x[1])]
        names_dict = {i: name for i, name in enumerate(class_names)}

        yolo_detect_yaml = yolo_detect_dir / "data.yaml"
        with open(yolo_detect_yaml, "w", encoding="utf-8") as f:
            f.write(f"path: {yolo_detect_dir.resolve().as_posix()}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            f.write("test: images/test\n")
            f.write(f"nc: {len(class_names)}\n")
            f.write(f"names: {json.dumps(names_dict)}\n")

        yolo_obb_yaml = yolo_obb_dir / "data.yaml"
        with open(yolo_obb_yaml, "w", encoding="utf-8") as f:
            f.write(f"path: {yolo_obb_dir.resolve().as_posix()}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            f.write("test: images/test\n")
            f.write(f"nc: {len(class_names)}\n")
            f.write(f"names: {json.dumps(names_dict)}\n")

        meta = {
            "dataset_version": "synthetic-motif-dataset-v1.0.0",
            "total_samples": self.total_samples,
            "master_seed": self.master_seed,
            "train_samples": n_train,
            "val_samples": n_val,
            "test_samples": n_test,
            "total_target_instances": total_target_instances,
            "total_hard_negative_instances": total_hard_negative_instances,
            "empty_negative_samples": empty_negative_samples_count,
            "hard_negative_only_samples": hard_negative_only_samples_count,
            "mixed_hard_negative_samples": mixed_hard_negative_samples_count,
            "fingerprint": dataset_fingerprint,
            "yolo_detect_yaml": str(yolo_detect_yaml),
            "yolo_obb_yaml": str(yolo_obb_yaml),
        }

        print(f"Synthetic dataset build complete! Fingerprint: {dataset_fingerprint}")
        return meta
