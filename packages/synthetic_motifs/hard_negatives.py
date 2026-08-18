"""
Controlled Hard-Negative Registry and Primitives for Synthetic Motif Datasets.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import math
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel, Field, ConfigDict

from packages.synthetic_motifs.geometry import Point, Polygon
from packages.synthetic_motifs.registry import VisualCandidateKey, SyntheticMotifRegistry

VALID_17_KEYS = {k.value for k in VisualCandidateKey}


class HardNegativeFamilyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_negative_key: str
    near_target_keys: List[str]
    rationale: str
    generator_version: str = "procedural-motif-generator-v1.0.0"

    def validate_near_target_keys(self) -> bool:
        for k in self.near_target_keys:
            if k not in VALID_17_KEYS:
                raise ValueError(f"Invalid near_target_key '{k}'. Must be one of 17 VisualCandidateKey values.")
        return True


class HardNegativeRegistry:
    """Registry for controlled non-target visual distractor families."""

    def __init__(self) -> None:
        self._entries: Dict[str, HardNegativeFamilyEntry] = {}
        self._register_default_families()

    def _register_default_families(self) -> None:
        # A. radial_polygon_nonstar -> near star_like
        self.register(HardNegativeFamilyEntry(
            hard_negative_key="radial_polygon_nonstar",
            near_target_keys=["star_like"],
            rationale="7-point asymmetric or scalloped gear polygon breaking star symmetry."
        ))
        # B. radial_ornament_nonrosette -> near rosette_like
        self.register(HardNegativeFamilyEntry(
            hard_negative_key="radial_ornament_nonrosette",
            near_target_keys=["rosette_like"],
            rationale="Spiky concentric circular gear or ring lacking rosette petal geometry."
        ))
        # C. isolated_lozenge_pattern -> near lattice_like
        self.register(HardNegativeFamilyEntry(
            hard_negative_key="isolated_lozenge_pattern",
            near_target_keys=["lattice_like"],
            rationale="Single isolated lozenge element without repeating matrix structure."
        ))
        # D. octagonal_radial_variant -> near octagonal_form, star_like
        self.register(HardNegativeFamilyEntry(
            hard_negative_key="octagonal_radial_variant",
            near_target_keys=["octagonal_form", "star_like"],
            rationale="Notched/stepped irregular octagon resembling both octagonal form and star."
        ))
        # E. generic_branching_form -> near tree_like
        self.register(HardNegativeFamilyEntry(
            hard_negative_key="generic_branching_form",
            near_target_keys=["tree_like"],
            rationale="Simple Y-fork or zigzag stroke lacking trunk or foliage structure."
        ))

    def register(self, entry: HardNegativeFamilyEntry) -> None:
        entry.validate_near_target_keys()
        self._entries[entry.hard_negative_key] = entry

    def list_keys(self) -> List[str]:
        return list(self._entries.keys())

    def get(self, key: str) -> HardNegativeFamilyEntry:
        if key not in self._entries:
            raise KeyError(f"Hard negative key '{key}' not found in registry.")
        return self._entries[key]

    def generate_polygon(
        self,
        key: str,
        cx: float,
        cy: float,
        radius: float,
        rotation_deg: float = 0.0,
        rng: Optional[np.random.RandomState] = None
    ) -> Polygon:
        if rng is None:
            rng = np.random.RandomState()

        rad = math.radians(rotation_deg)

        if key == "radial_polygon_nonstar":
            # 7-point asymmetric polygon (odd points, non-star inner/outer radii)
            num_points = 7
            vertices = []
            for i in range(num_points * 2):
                angle = rad + i * (2.0 * math.pi / (num_points * 2))
                r = radius if (i % 2 == 0) else radius * 0.72
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                vertices.append((x, y))
            return Polygon(vertices)

        elif key == "radial_ornament_nonrosette":
            # 12-tooth spiky concentric gear ring
            num_teeth = 12
            vertices = []
            for i in range(num_teeth * 2):
                angle = rad + i * (2.0 * math.pi / (num_teeth * 2))
                r = radius if (i % 2 == 0) else radius * 0.45
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                vertices.append((x, y))
            return Polygon(vertices)

        elif key == "isolated_lozenge_pattern":
            # Single lozenge/rhombus
            w = radius * 1.2
            h = radius * 0.7
            raw = [(0.0, -h), (w, 0.0), (0.0, h), (-w, 0.0)]
            vertices = []
            for rx, ry in raw:
                x = cx + rx * math.cos(rad) - ry * math.sin(rad)
                y = cy + rx * math.sin(rad) + ry * math.cos(rad)
                vertices.append((x, y))
            return Polygon(vertices)

        elif key == "octagonal_radial_variant":
            # Notched 8-point stepped polygon
            vertices = []
            for i in range(8):
                angle = rad + i * (math.pi / 4.0) + (0.1 if i % 2 == 1 else 0.0)
                r = radius * (1.0 if i % 2 == 0 else 0.82)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                vertices.append((x, y))
            return Polygon(vertices)

        elif key == "generic_branching_form":
            # Y-fork polyline expanded to polygon
            stem_h = radius * 1.2
            arm_w = radius * 0.6
            raw = [
                (-0.1 * radius, -stem_h),
                (0.1 * radius, -stem_h),
                (0.1 * radius, 0.0),
                (arm_w, arm_w),
                (arm_w - 0.15 * radius, arm_w + 0.15 * radius),
                (0.0, 0.25 * radius),
                (-arm_w + 0.15 * radius, arm_w + 0.15 * radius),
                (-arm_w, arm_w),
                (-0.1 * radius, 0.0)
            ]
            vertices = []
            for rx, ry in raw:
                x = cx + rx * math.cos(rad) - ry * math.sin(rad)
                y = cy + rx * math.sin(rad) + ry * math.cos(rad)
                vertices.append((x, y))
            return Polygon(vertices)

        else:
            raise KeyError(f"Unsupported hard negative polygon key '{key}'.")
