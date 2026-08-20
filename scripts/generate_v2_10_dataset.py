"""
V2-10 Dataset Generation Script with Domain Randomization V2.
Generates 5,000 high-realism synthetic carpet images across 17 stratified classes.
Produces QA contact sheet (4x6) and bbox overlay validation samples.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import sys
import os
import json
import time
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
sys.path.insert(0, str(ROOT_DIR))

from packages.synthetic_motifs.registry import SyntheticMotifRegistry, VisualCandidateKey
from packages.synthetic_motifs.hard_negatives import HardNegativeRegistry
from packages.synthetic_motifs.geometry import Polygon, BoundingBox, OrientedBoundingBox
from packages.synthetic_motifs.renderers.base import VectorRenderer
from packages.synthetic_motifs.randomization_v2 import (
    ANTIQUE_NATURAL_PALETTES,
    DomainRandomizationV2Config,
    ProceduralWeaveTextureEngine,
    AbrasionWearEngine,
    ColorAgingFadingEngine,
    HandmadeElasticWarpEngine,
    CameraOpticalChainEngine,
    DirectionalPolicyEngine,
)


CLASS_NAMES = [
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
    "vine_scroll_like"
]

CLASS_MAP = {name: i for i, name in enumerate(CLASS_NAMES)}
ID_TO_CLASS = {i: name for i, name in enumerate(CLASS_NAMES)}


class SceneComposerV2:
    """Generates scenes with stratified class coverage and full V2 physical/optical randomization."""

    def __init__(self, config: Optional[DomainRandomizationV2Config] = None):
        self.config = config or DomainRandomizationV2Config()
        self.registry = SyntheticMotifRegistry()
        self.hard_negative_registry = HardNegativeRegistry()

    def generate_scene(
        self,
        width: int = 640,
        height: int = 640,
        seed: int = 42,
        target_primary_key: Optional[str] = None,
        is_negative: bool = False,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Dict[str, Any]]:
        rng = np.random.RandomState(int(seed) % (2**31 - 1))
        palette = ANTIQUE_NATURAL_PALETTES[int(rng.choice(len(ANTIQUE_NATURAL_PALETTES)))]

        # Base canvas
        canvas = VectorRenderer.create_canvas(width, height, background_rgb=palette["background"])

        # Border layout
        border_w = int(min(width, height) * float(rng.uniform(0.08, 0.14)))
        guard_w = int(border_w * 0.28)

        # Outer border
        cv2.rectangle(canvas, (0, 0), (width, height), palette["border_outer"], -1)
        # Inner Field
        fx1, fy1 = border_w, border_w
        fx2, fy2 = width - border_w, height - border_w
        cv2.rectangle(canvas, (fx1 - guard_w, fy1 - guard_w), (fx2 + guard_w, fy2 + guard_w), palette["border_inner"], -1)
        cv2.rectangle(canvas, (fx1, fy1), (fx2, fy2), palette["field"], -1)

        raw_polygons: List[Polygon] = []
        raw_keys: List[str] = []

        if not is_negative:
            # Determine motifs to place
            motifs_to_place = []
            if target_primary_key:
                motifs_to_place.append(target_primary_key)
            
            # Add 1 to 4 complementary motifs
            num_additional = int(rng.randint(1, 4))
            for _ in range(num_additional):
                k = CLASS_NAMES[int(rng.choice(len(CLASS_NAMES)))]
                motifs_to_place.append(k)

            # Placement layout logic
            for idx, m_key in enumerate(motifs_to_place):
                # Sample rotation following directional policy
                rot_deg = DirectionalPolicyEngine.sample_rotation(
                    m_key, rng, max_locked_angle=self.config.direction_locked_angle_max
                )

                if m_key in {"medallion_like", "niche_like"} and idx == 0:
                    # Central or focal placement
                    cx = width / 2.0
                    cy = height * (0.50 if m_key == "medallion_like" else 0.52)
                    r = min(width, height) * float(rng.uniform(0.24, 0.36))
                elif m_key == "tree_like":
                    # Upright central or column placement
                    cx = float(rng.uniform(width * 0.32, width * 0.68))
                    cy = float(rng.uniform(height * 0.45, height * 0.65))
                    r = min(width, height) * float(rng.uniform(0.18, 0.30))
                elif m_key == "vine_scroll_like":
                    # Placed along border or field edge
                    cx = float(rng.uniform(fx1 + 30, fx2 - 30))
                    cy = float(rng.uniform(fy1 + 30, fy2 - 30))
                    r = min(width, height) * float(rng.uniform(0.12, 0.22))
                else:
                    # General field placement
                    r = min(width, height) * float(rng.uniform(0.08, 0.18))
                    cx = float(rng.uniform(fx1 + r, fx2 - r))
                    cy = float(rng.uniform(fy1 + r, fy2 - r))

                try:
                    poly = self.registry.generate_polygon(
                        VisualCandidateKey(m_key), cx, cy, r, rotation_deg=rot_deg
                    )
                    raw_polygons.append(poly)
                    raw_keys.append(m_key)
                except Exception:
                    pass

        # Render vector polygons with natural antique palette colors
        for idx, (poly, key) in enumerate(zip(raw_polygons, raw_keys)):
            fill_color = palette["motifs"][idx % len(palette["motifs"])]
            stroke_color = palette["border_outer"]
            VectorRenderer.render_polygon_fill(canvas, poly, fill_rgb=fill_color)
            VectorRenderer.render_polygon_stroke(canvas, poly, stroke_rgb=stroke_color, thickness=2)

        # -------------------------------------------------------------
        # DOMAIN RANDOMIZATION V2 PIPELINE
        # -------------------------------------------------------------
        spec: Dict[str, Any] = {"palette": palette["name"], "seed": seed}

        # 1. Handmade Elastic Warp & Knot Jitter + Perspective Tilt
        if self.config.warp_enabled:
            canvas, raw_polygons, warp_info = HandmadeElasticWarpEngine.apply_elastic_and_jitter(
                canvas,
                raw_polygons,
                max_displacement=self.config.elastic_displacement_max,
                jitter_max=self.config.knot_jitter_max,
                tilt_deg_max=self.config.perspective_tilt_deg_max,
                rng=rng,
            )
            spec["warp"] = warp_info

        # 2. Procedural Weave & Knot Texture + Vignette
        if self.config.texture_enabled:
            knot_f = float(rng.uniform(self.config.knot_frequency_range[0], self.config.knot_frequency_range[1]))
            knot_a = float(rng.uniform(self.config.knot_amplitude_range[0], self.config.knot_amplitude_range[1]))
            weave_tex = ProceduralWeaveTextureEngine.generate_weave_texture(
                width, height, knot_freq=knot_f, amplitude=knot_a, rng=rng
            )
            canvas = np.clip(canvas.astype(np.float32) + weave_tex, 0, 255).astype(np.uint8)
            vignette_int = float(rng.uniform(self.config.vignette_intensity_range[0], self.config.vignette_intensity_range[1]))
            canvas = ProceduralWeaveTextureEngine.apply_vignette(canvas, intensity=vignette_int)
            spec["texture"] = {"knot_freq": knot_f, "knot_amplitude": knot_a, "vignette_intensity": vignette_int}

        # 3. Fiber Abrasion & Distressed Wear
        if self.config.wear_enabled and rng.uniform(0, 1) < self.config.wear_prob:
            canvas, wear_info = AbrasionWearEngine.apply_abrasion(
                canvas, base_canvas_color=palette["background"], max_fraction=self.config.wear_max_fraction, rng=rng
            )
            spec["wear"] = wear_info

        # 4. Regional Chromatic Aging & Fading
        if self.config.fading_enabled:
            canvas, fade_info = ColorAgingFadingEngine.apply_fading(
                canvas,
                gamma_range=self.config.gamma_range,
                sat_range=self.config.saturation_range,
                grid_size=self.config.regional_fade_cells,
                rng=rng,
            )
            spec["fading"] = fade_info

        # 5. Camera & Optical Chain (Defocus, Light Gradient, Sensor Noise, JPEG Artifacts)
        if self.config.camera_chain_enabled:
            canvas, cam_info = CameraOpticalChainEngine.apply_chain(
                canvas,
                light_strength=float(rng.uniform(self.config.lighting_gradient_strength[0], self.config.lighting_gradient_strength[1])),
                defocus_prob=self.config.defocus_blur_prob,
                sensor_noise_prob=self.config.sensor_noise_prob,
                jpeg_quality_range=self.config.jpeg_quality_range,
                rng=rng,
            )
            spec["camera"] = cam_info

        # 6. Extract Valid Ground Truth Annotations
        instances: List[Dict[str, Any]] = []
        for poly, key in zip(raw_polygons, raw_keys):
            pts = np.array(poly.vertices, dtype=np.float32)
            x_min = float(np.clip(np.min(pts[:, 0]), 0.0, float(width - 1)))
            y_min = float(np.clip(np.min(pts[:, 1]), 0.0, float(height - 1)))
            x_max = float(np.clip(np.max(pts[:, 0]), 0.0, float(width - 1)))
            y_max = float(np.clip(np.max(pts[:, 1]), 0.0, float(height - 1)))

            bw = x_max - x_min
            bh = y_max - y_min
            if bw < 10 or bh < 10:
                continue

            cx_norm = (x_min + bw / 2.0) / width
            cy_norm = (y_min + bh / 2.0) / height
            w_norm = bw / width
            h_norm = bh / height

            instances.append({
                "class_name": key,
                "class_id": CLASS_MAP[key],
                "bbox_xyxy": [round(x_min, 1), round(y_min, 1), round(x_max, 1), round(y_max, 1)],
                "bbox_yolo": [round(cx_norm, 6), round(cy_norm, 6), round(w_norm, 6), round(h_norm, 6)],
            })

        return canvas, instances, spec


def build_v2_10_dataset(
    output_base_dir: Path,
    total_images: int = 5000,
    master_seed: int = 42000,
):
    detect_dir = output_base_dir / "yolo_detect"
    splits = ["train", "val", "test"]
    n_train = 3500
    n_val = 750
    n_test = 750

    for s in splits:
        (detect_dir / "images" / s).mkdir(parents=True, exist_ok=True)
        (detect_dir / "labels" / s).mkdir(parents=True, exist_ok=True)

    composer = SceneComposerV2()
    class_box_counts = {name: {"train": 0, "val": 0, "test": 0, "total": 0} for name in CLASS_NAMES}
    split_assignments = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test

    print(f"Generating V2-10 Dataset: {total_images} images (train={n_train}, val={n_val}, test={n_test})...")
    t0 = time.time()

    saved_samples_meta = []
    fingerprint_hasher = hashlib.sha256()

    for idx in range(total_images):
        seed = master_seed + idx * 31337
        split = split_assignments[idx]
        sample_id = f"v210_{idx+1:06d}"

        # Stratified primary class cycling to guarantee >= 200 bboxes per class
        primary_class = CLASS_NAMES[idx % len(CLASS_NAMES)]
        is_negative = (idx % 25 == 0)  # 4% empty background scenes

        img, instances, spec = composer.generate_scene(
            width=640,
            height=640,
            seed=seed,
            target_primary_key=primary_class if not is_negative else None,
            is_negative=is_negative,
        )

        # Write image
        img_rel = f"images/{split}/{sample_id}.jpg"
        img_path = detect_dir / img_rel
        cv2.imwrite(str(img_path), img)

        # Write YOLO label
        lbl_rel = f"labels/{split}/{sample_id}.txt"
        lbl_path = detect_dir / lbl_rel
        with open(lbl_path, "w", encoding="utf-8") as f_lbl:
            for inst in instances:
                c_id = inst["class_id"]
                c_name = inst["class_name"]
                cx, cy, w, h = inst["bbox_yolo"]
                f_lbl.write(f"{c_id} {cx} {cy} {w} {h}\n")
                class_box_counts[c_name][split] += 1
                class_box_counts[c_name]["total"] += 1

        fingerprint_hasher.update(f"{sample_id}:{seed}:{len(instances)}".encode("utf-8"))

        if (idx + 1) % 500 == 0 or idx == total_images - 1:
            elapsed = time.time() - t0
            print(f"  [{idx+1}/{total_images}] images generated ({elapsed:.1f}s, {idx+1/elapsed:.1f} img/s)...")

    # Generate data.yaml and dataset.yaml
    names_dict = {i: name for i, name in enumerate(CLASS_NAMES)}
    yaml_content = f"""path: {detect_dir.resolve().as_posix()}
train: images/train
val: images/val
test: images/test
nc: {len(CLASS_NAMES)}
names: {json.dumps(names_dict)}
"""
    with open(detect_dir / "data.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_content)
    with open(detect_dir / "dataset.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # Save manifest
    manifest_data = {
        "dataset_version": "v2-10-domain-randomization-v2.0.0",
        "master_seed": master_seed,
        "total_images": total_images,
        "splits": {
            "train": n_train,
            "val": n_val,
            "test": n_test,
        },
        "classes": CLASS_NAMES,
        "class_box_counts": class_box_counts,
        "total_bounding_boxes": sum(v["total"] for v in class_box_counts.values()),
        "dataset_sha256_fingerprint": fingerprint_hasher.hexdigest(),
        "randomization_v2_parameters": {
            "procedural_texture": {
                "knot_frequency_range": [3.0, 7.0],
                "knot_amplitude_range": [0.04, 0.12],
                "vignette_intensity_range": [0.10, 0.35],
                "leakage_constraint": "100% synthetic mathematical noise; zero real carpet pixels sampled."
            },
            "abrasion_wear": {
                "wear_probability": 0.70,
                "wear_max_fraction": 0.25,
                "blend_style": "antique base canvas tint & distressed fiber erosion"
            },
            "chromatic_aging": {
                "palettes": [p["name"] for p in ANTIQUE_NATURAL_PALETTES],
                "gamma_range": [0.80, 1.25],
                "saturation_range": [0.65, 1.15],
                "regional_grid_cells": [6, 6]
            },
            "handmade_elastic_warp": {
                "elastic_displacement_max_px": 4.0,
                "knot_jitter_max_px": 2.0,
                "perspective_tilt_deg_max": 12.0
            },
            "camera_optical_chain": {
                "lighting_gradient_strength": [0.10, 0.28],
                "defocus_blur_sigma": [0.4, 1.3],
                "sensor_noise_sigma": [2.5, 9.0],
                "jpeg_quality_range": [60, 95]
            },
            "directional_policy": {
                "tree_like": "+/- 8 deg upright",
                "niche_like": "+/- 8 deg upright (no inverted arch)",
                "human_figure_like_geometric": "+/- 8 deg upright",
                "symmetric_classes": "free isotropic / 4-way rotation"
            }
        },
        "counting_convention": {
            "raw_proposal_count": "Total candidate boxes emitted by YOLO forward pass prior to filtering",
            "post_verifier_count": "Final candidates retained after CV morphology/contour gating",
            "confidence_threshold": "Operational inference threshold (default: 0.10/0.25) and auto-confirm threshold (0.85)"
        }
    }

    manifest_path = output_base_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"V2-10 Dataset successfully built in {time.time() - t0:.1f}s! Manifest saved to {manifest_path}")
    return manifest_data


def generate_qa_artifacts(
    dataset_dir: Path,
    qa_output_dir: Path,
):
    qa_output_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir = qa_output_dir / "qa-bbox-samples"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    detect_dir = dataset_dir / "yolo_detect"
    train_imgs = sorted((detect_dir / "images" / "train").glob("*.jpg"))

    # 1. Generate Contact Sheet (4x6 = 24 images)
    print("Generating QA Contact Sheet (4x6 grid of 24 images)...")
    selected_24 = [train_imgs[int(i)] for i in np.linspace(0, len(train_imgs) - 1, 24)]
    
    cell_w, cell_h = 240, 240
    sheet = np.zeros((4 * cell_h, 6 * cell_w, 3), dtype=np.uint8)

    for idx, p in enumerate(selected_24):
        im = cv2.imread(str(p))
        im_thumb = cv2.resize(im, (cell_w, cell_h))
        # Draw cell index
        cv2.putText(im_thumb, f"#{idx+1}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(im_thumb, f"#{idx+1}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1, cv2.LINE_AA)
        
        row = idx // 6
        col = idx % 6
        sheet[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w] = im_thumb

    contact_path = qa_output_dir / "qa-contact-sheet.png"
    cv2.imwrite(str(contact_path), sheet)
    print(f"Contact sheet saved to: {contact_path}")

    # 2. Generate 8 Bounding Box Overlay Samples
    print("Generating 8 BBox Overlay verification samples...")
    selected_8 = [train_imgs[int(i)] for i in np.linspace(10, len(train_imgs) - 20, 8)]

    for s_idx, p in enumerate(selected_8):
        im = cv2.imread(str(p))
        h, w = im.shape[:2]
        lbl_file = detect_dir / "labels" / "train" / f"{p.stem}.txt"

        if lbl_file.exists():
            with open(lbl_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        c_id = int(parts[0])
                        c_name = ID_TO_CLASS.get(c_id, f"cls_{c_id}")
                        cx, cy, bw, bh = [float(v) for v in parts[1:5]]
                        x1 = int((cx - bw / 2.0) * w)
                        y1 = int((cy - bh / 2.0) * h)
                        x2 = int((cx + bw / 2.0) * w)
                        y2 = int((cy + bh / 2.0) * h)

                        # Draw box
                        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 60), 2, cv2.LINE_AA)
                        # Draw label tag
                        tag = f"{c_name}"
                        cv2.putText(im, tag, (x1 + 4, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
                        cv2.putText(im, tag, (x1 + 4, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        sample_out_path = overlay_dir / f"sample_{s_idx+1}_{p.stem}.png"
        cv2.imwrite(str(sample_out_path), im)

    print(f"8 BBox samples saved to: {overlay_dir}")


if __name__ == "__main__":
    out_dir = ROOT_DIR / "artifacts" / "v2-10" / "dataset"
    qa_dir = ROOT_DIR / "data" / "validation" / "v2-10"
    
    meta = build_v2_10_dataset(out_dir, total_images=5000, master_seed=42000)
    generate_qa_artifacts(out_dir, qa_dir)
