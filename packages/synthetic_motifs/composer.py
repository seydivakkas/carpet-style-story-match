"""
CarpetComposer — Structured Scene Composition Engine for Synthetic Motifs.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import List, Tuple, Dict, Any, Optional
import hashlib
import json
import math
import numpy as np
import cv2
from packages.synthetic_motifs.geometry import Polygon, BoundingBox, OrientedBoundingBox
from packages.synthetic_motifs.registry import SyntheticMotifRegistry, VisualCandidateKey
from packages.synthetic_motifs.hard_negatives import HardNegativeRegistry, HardNegativeFamilyEntry
from packages.synthetic_motifs.renderers.base import VectorRenderer
from packages.synthetic_motifs.annotations import SyntheticMotifInstanceGT, HardNegativeProvenanceGT


COLOR_PALETTES = [
    # Classic Madder & Indigo
    {
        "background": (235, 230, 215),      # Cream
        "field": (30, 35, 140),             # Madder Red (BGR)
        "border_outer": (130, 60, 20),      # Indigo Blue (BGR)
        "border_inner": (210, 190, 160),    # Soft Gold
        "motifs": [(230, 220, 200), (35, 140, 180), (130, 60, 20), (40, 110, 40), (20, 30, 130)],
    },
    # Terracotta & Sage
    {
        "background": (220, 215, 200),
        "field": (40, 75, 160),             # Terracotta
        "border_outer": (90, 120, 80),      # Sage Green
        "border_inner": (230, 220, 200),
        "motifs": [(240, 235, 220), (30, 35, 130), (90, 120, 80), (30, 150, 200)],
    },
    # Deep Night & Ochre
    {
        "background": (30, 30, 40),
        "field": (50, 40, 30),              # Deep Navy
        "border_outer": (30, 140, 200),     # Ochre
        "border_inner": (210, 200, 180),
        "motifs": [(230, 215, 190), (30, 140, 200), (40, 50, 160), (60, 130, 60)],
    },
]


class CarpetComposer:
    """Composes layered synthetic carpet visual scenes with exact ground truth annotations."""

    def __init__(
        self,
        registry: Optional[SyntheticMotifRegistry] = None,
        hard_negative_registry: Optional[HardNegativeRegistry] = None,
    ):
        self.registry = registry or SyntheticMotifRegistry()
        self.hard_negative_registry = hard_negative_registry or HardNegativeRegistry()

    def compose_scene(
        self,
        width: int = 640,
        height: int = 640,
        seed: int = 42,
        layout_type: Optional[str] = None,
        force_keys: Optional[List[VisualCandidateKey]] = None,
        is_negative: bool = False,
        hard_negative_mode: Optional[str] = None,  # None, "HARD_NEGATIVE_ONLY", "MIXED_HARD_NEGATIVE"
    ) -> Tuple[np.ndarray, List[SyntheticMotifInstanceGT], List[HardNegativeProvenanceGT], Dict[str, Any], str]:
        """Composes a complete synthetic carpet scene.
        
        Returns:
            image: np.ndarray (H, W, 3) BGR uint8
            instances: List[SyntheticMotifInstanceGT] (POSITIVE target annotations ONLY)
            hard_negatives: List[HardNegativeProvenanceGT] (NON-TARGET hard negative background objects)
            scene_spec: Dict[str, Any]
            scene_signature: str (hash of canonical geometry/parameters before photometric noise)
        """
        rng = np.random.RandomState(int(seed) % (2**31 - 1))
        palette = COLOR_PALETTES[int(rng.choice(len(COLOR_PALETTES)))]

        # Available layout strategies
        layouts = [
            "MEDALLION_WITH_CORNERS",
            "NICHE_ARCH",
            "REPEATING_FIELD_GRID",
            "ALLOVER_LATTICE",
            "MIXED_SCATTERED",
        ]

        if hard_negative_mode == "HARD_NEGATIVE_ONLY":
            layout_type = "HARD_NEGATIVE_SAMPLE"
            is_negative = True
        elif hard_negative_mode == "MIXED_HARD_NEGATIVE":
            if layout_type is None:
                layout_type = "MIXED_HARD_NEGATIVE"
        elif is_negative:
            layout_type = "NEGATIVE_BORDER_ONLY" if rng.uniform(0, 1) < 0.5 else "NEGATIVE_DISTRACTOR"
        elif layout_type is None:
            layout_type = str(rng.choice(layouts))

        # Base canvas
        canvas = VectorRenderer.create_canvas(width, height, background_rgb=palette["background"])
        
        # 1. Render Outer & Inner Borders
        border_w = int(min(width, height) * float(rng.uniform(0.08, 0.14)))
        guard_w = int(border_w * 0.3)
        
        # Outer Border Rect
        cv2.rectangle(canvas, (0, 0), (width, height), palette["border_outer"], -1)
        # Inner Field Rect
        fx1, fy1 = border_w, border_w
        fx2, fy2 = width - border_w, height - border_w
        cv2.rectangle(canvas, (fx1 - guard_w, fy1 - guard_w), (fx2 + guard_w, fy2 + guard_w), palette["border_inner"], -1)
        cv2.rectangle(canvas, (fx1, fy1), (fx2, fy2), palette["field"], -1)

        instances: List[SyntheticMotifInstanceGT] = []
        hard_negatives: List[HardNegativeProvenanceGT] = []
        raw_polygons: List[Polygon] = []
        inst_keys: List[str] = []
        inst_params: List[Dict[str, Any]] = []
        hn_specs: List[Dict[str, Any]] = []

        is_true_negative = is_negative and (hard_negative_mode != "MIXED_HARD_NEGATIVE")

        if is_true_negative:
            if layout_type == "NEGATIVE_DISTRACTOR":
                for _ in range(int(rng.randint(3, 8))):
                    rx = float(rng.uniform(fx1 + 20, fx2 - 20))
                    ry = float(rng.uniform(fy1 + 20, fx2 - 20))
                    rw = float(rng.uniform(15, 40))
                    c = palette["motifs"][int(rng.choice(len(palette["motifs"])))]
                    cv2.rectangle(canvas, (int(rx - rw), int(ry - rw)), (int(rx + rw), int(ry + rw)), c, 2)
        elif layout_type == "MEDALLION_WITH_CORNERS":
            # Central Medallion
            center_options = [
                VisualCandidateKey.MEDALLION_LIKE,
                VisualCandidateKey.STAR_LIKE,
                VisualCandidateKey.OCTAGONAL_FORM,
                VisualCandidateKey.ROSETTE_LIKE,
                VisualCandidateKey.LOZENGE_LIKE,
            ]
            center_key = force_keys[0] if (force_keys and len(force_keys) > 0) else center_options[int(rng.choice(len(center_options)))]
            r_center = min(width, height) * float(rng.uniform(0.18, 0.32))
            cx, cy = width / 2.0, height / 2.0
            p_center = self.registry.generate_polygon(
                center_key, cx, cy, r_center, rotation_deg=float(rng.uniform(-45, 45))
            )
            raw_polygons.append(p_center)
            inst_keys.append(center_key.value if hasattr(center_key, 'value') else str(center_key))
            inst_params.append({"cx": cx, "cy": cy, "radius": r_center, "layout_role": "central_medallion"})

            # 4 Corner Motifs
            corner_options = [
                VisualCandidateKey.PALMETTE_LIKE,
                VisualCandidateKey.HOOK_LIKE,
                VisualCandidateKey.HORN_LIKE,
                VisualCandidateKey.LOZENGE_LIKE,
                VisualCandidateKey.ROSETTE_LIKE,
            ]
            corner_key = force_keys[1] if (force_keys and len(force_keys) > 1) else corner_options[int(rng.choice(len(corner_options)))]
            r_corner = min(width, height) * float(rng.uniform(0.08, 0.14))
            corner_coords = [
                (fx1 + r_corner * 0.9, fy1 + r_corner * 0.9, 135.0),
                (fx2 - r_corner * 0.9, fy1 + r_corner * 0.9, -135.0),
                (fx2 - r_corner * 0.9, fy2 - r_corner * 0.9, -45.0),
                (fx1 + r_corner * 0.9, fy2 - r_corner * 0.9, 45.0),
            ]
            for ccx, ccy, crot in corner_coords:
                p_corner = self.registry.generate_polygon(corner_key, ccx, ccy, r_corner, rotation_deg=crot)
                raw_polygons.append(p_corner)
                inst_keys.append(corner_key.value if hasattr(corner_key, 'value') else str(corner_key))
                inst_params.append({"cx": ccx, "cy": ccy, "radius": r_corner, "layout_role": "corner_spandrel"})

        elif layout_type == "NICHE_ARCH":
            # Niche arch
            niche_key = VisualCandidateKey.NICHE_LIKE
            cx, cy = width / 2.0, height * 0.52
            r_niche = min(width, height) * float(rng.uniform(0.32, 0.40))
            p_niche = self.registry.generate_polygon(niche_key, cx, cy, r_niche)
            raw_polygons.append(p_niche)
            inst_keys.append(niche_key.value)
            inst_params.append({"cx": cx, "cy": cy, "radius": r_niche, "layout_role": "niche_arch"})

            # Inner tree / figure / lotus inside arch
            inner_options = [
                VisualCandidateKey.TREE_LIKE,
                VisualCandidateKey.HUMAN_FIGURE_LIKE_GEOMETRIC,
                VisualCandidateKey.LOTUS_LIKE,
                VisualCandidateKey.PALMETTE_LIKE,
            ]
            inner_key = force_keys[0] if (force_keys and len(force_keys) > 0) else inner_options[int(rng.choice(len(inner_options)))]
            r_inner = r_niche * float(rng.uniform(0.35, 0.50))
            p_inner = self.registry.generate_polygon(inner_key, cx, cy + r_niche * 0.1, r_inner)
            raw_polygons.append(p_inner)
            inst_keys.append(inner_key.value if hasattr(inner_key, 'value') else str(inner_key))
            inst_params.append({"cx": cx, "cy": cy + r_niche * 0.1, "radius": r_inner, "layout_role": "niche_inner"})

        elif layout_type == "REPEATING_FIELD_GRID":
            # Grid of repeated motifs
            all_k = self.registry.list_keys()
            grid_key = force_keys[0] if (force_keys and len(force_keys) > 0) else all_k[int(rng.choice(len(all_k)))]
            rows, cols = int(rng.randint(2, 4)), int(rng.randint(2, 4))
            gx = np.linspace(fx1 + (fx2 - fx1) / (cols * 2), fx2 - (fx2 - fx1) / (cols * 2), cols)
            gy = np.linspace(fy1 + (fy2 - fy1) / (rows * 2), fy2 - (fy2 - fy1) / (rows * 2), rows)
            r_grid = min((fx2 - fx1) / cols, (fy2 - fy1) / rows) * float(rng.uniform(0.30, 0.44))

            for r_y in gy:
                for r_x in gx:
                    p_grid = self.registry.generate_polygon(
                        grid_key, float(r_x), float(r_y), float(r_grid), rotation_deg=float(rng.uniform(-30, 30))
                    )
                    raw_polygons.append(p_grid)
                    inst_keys.append(grid_key.value if hasattr(grid_key, 'value') else str(grid_key))
                    inst_params.append({"cx": float(r_x), "cy": float(r_y), "radius": float(r_grid), "layout_role": "grid_cell"})

        elif layout_type == "ALLOVER_LATTICE":
            # Lattice structure
            lattice_key = VisualCandidateKey.LATTICE_LIKE
            cx, cy = width / 2.0, height / 2.0
            r_lat = min(width, height) * float(rng.uniform(0.32, 0.42))
            p_lat = self.registry.generate_polygon(lattice_key, cx, cy, r_lat)
            raw_polygons.append(p_lat)
            inst_keys.append(lattice_key.value)
            inst_params.append({"cx": cx, "cy": cy, "radius": r_lat, "layout_role": "lattice_field"})

            # Add decorative rosette or lozenge inside
            focal_key = force_keys[0] if (force_keys and len(force_keys) > 0) else VisualCandidateKey.ROSETTE_LIKE
            r_foc = r_lat * 0.35
            p_foc = self.registry.generate_polygon(focal_key, cx, cy, r_foc)
            raw_polygons.append(p_foc)
            inst_keys.append(focal_key.value if hasattr(focal_key, 'value') else str(focal_key))
            inst_params.append({"cx": cx, "cy": cy, "radius": r_foc, "layout_role": "lattice_focal"})

        else:  # MIXED_SCATTERED or MIXED_HARD_NEGATIVE
            n_motifs = int(rng.randint(2, 5))
            all_k = self.registry.list_keys()
            for i in range(n_motifs):
                m_key = force_keys[i % len(force_keys)] if force_keys else all_k[int(rng.choice(len(all_k)))]
                r_scat = min(width, height) * float(rng.uniform(0.08, 0.20))
                scx = float(rng.uniform(fx1 + r_scat, fx2 - r_scat))
                scy = float(rng.uniform(fy1 + r_scat, fy2 - r_scat))
                p_scat = self.registry.generate_polygon(
                    m_key, scx, scy, r_scat, rotation_deg=float(rng.uniform(-180, 180))
                )
                raw_polygons.append(p_scat)
                inst_keys.append(m_key.value if hasattr(m_key, 'value') else str(m_key))
                inst_params.append({"cx": scx, "cy": scy, "radius": r_scat, "layout_role": "scattered"})


        # Render all target instances onto canvas layer by layer
        for idx, (poly, key, params) in enumerate(zip(raw_polygons, inst_keys, inst_params)):
            inst_color = palette["motifs"][idx % len(palette["motifs"])]
            stroke_color = palette["border_outer"]
            VectorRenderer.render_polygon_fill(canvas, poly, fill_rgb=inst_color)
            VectorRenderer.render_polygon_stroke(canvas, poly, stroke_rgb=stroke_color, thickness=2)

            # Generate instance annotations
            bbox = poly.get_bounding_box()
            obb = poly.get_oriented_bounding_box()
            instance_id = f"inst_{idx + 1:04d}_{key}"

            inst_gt = SyntheticMotifInstanceGT(
                instance_id=instance_id,
                visual_candidate_key=key,
                bbox_xyxy=bbox.to_xyxy(),
                bbox_normalized=bbox.to_normalized(width, height),
                polygon=poly.to_list(),
                obb=obb.to_list(),
                obb_normalized=obb.to_normalized(width, height),
                full_geometry=poly.to_list(),
                visible_fraction=1.0,
                is_truncated=False,
                is_occluded=False,
                ignore=False,
                render_parameters=params,
                transform_provenance={"stage": "composer_canonical"},
            )
            instances.append(inst_gt)

        # 2. Render Controlled Hard Negatives (Background non-target visual distractors)
        should_render_hn = (
            hard_negative_mode in ("HARD_NEGATIVE_ONLY", "MIXED_HARD_NEGATIVE")
            or (not is_negative and rng.uniform(0, 1) < 0.20)
        )

        if should_render_hn:
            hn_keys_available = self.hard_negative_registry.list_keys()
            num_hn = int(rng.randint(1, 3)) if hard_negative_mode else 1
            for hn_idx in range(num_hn):
                hn_key = str(rng.choice(hn_keys_available))
                hn_entry = self.hard_negative_registry.get(hn_key)

                hn_cx = float(rng.uniform(fx1 + 40, fx2 - 40))
                hn_cy = float(rng.uniform(fy1 + 40, fy2 - 40))
                hn_r = min(width, height) * float(rng.uniform(0.08, 0.18))
                hn_rot = float(rng.uniform(-180, 180))

                poly_hn = self.hard_negative_registry.generate_polygon(
                    hn_key, hn_cx, hn_cy, hn_r, rotation_deg=hn_rot, rng=rng
                )

                # Render onto image canvas (pixels exist)
                hn_color = palette["motifs"][(len(instances) + hn_idx) % len(palette["motifs"])]
                VectorRenderer.render_polygon_fill(canvas, poly_hn, fill_rgb=hn_color)
                VectorRenderer.render_polygon_stroke(canvas, poly_hn, stroke_rgb=palette["border_inner"], thickness=2)

                hn_bbox = poly_hn.get_bounding_box()
                hn_id = f"hn_{hn_idx + 1:04d}_{hn_key}"

                hn_gt = HardNegativeProvenanceGT(
                    hard_negative_id=hn_id,
                    hard_negative_key=hn_key,
                    near_target_keys=hn_entry.near_target_keys,
                    bbox_xyxy=hn_bbox.to_xyxy(),
                    polygon=poly_hn.to_list(),
                    render_parameters={
                        "cx": hn_cx,
                        "cy": hn_cy,
                        "radius": hn_r,
                        "rotation_deg": hn_rot,
                        "rationale": hn_entry.rationale,
                    }
                )
                hard_negatives.append(hn_gt)
                hn_specs.append({"id": hn_id, "key": hn_key, "near": hn_entry.near_target_keys})

        scene_spec = {
            "layout_type": layout_type,
            "width": width,
            "height": height,
            "instance_count": len(instances),
            "hard_negative_count": len(hard_negatives),
            "keys_present": list(set(inst_keys)),
            "hard_negative_keys_present": [hn.hard_negative_key for hn in hard_negatives],
            "border_width": border_w,
        }

        # Deterministic scene signature based on geometry/parameters BEFORE photometric noise
        sig_data = {
            "layout": layout_type,
            "border_w": border_w,
            "instances": [{"k": k, "p": p} for k, p in zip(inst_keys, inst_params)],
            "hard_negatives": hn_specs,
            "seed_entropy": int(seed) if is_negative or len(instances) == 0 else 0,
        }
        scene_signature = hashlib.sha256(json.dumps(sig_data, sort_keys=True).encode("utf-8")).hexdigest()

        return canvas, instances, hard_negatives, scene_spec, scene_signature

