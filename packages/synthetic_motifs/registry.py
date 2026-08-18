"""
Synthetic Motif Registry.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from dataclasses import dataclass
from typing import Dict, Any, Type, List, Optional
from enum import Enum

from packages.synthetic_motifs.geometry import Polygon
from packages.synthetic_motifs.primitives.geometric import (
    StarPrimitive,
    OctagonPrimitive,
    LozengePrimitive,
    RosettePrimitive,
    CombPrimitive,
    HookPrimitive,
    LatticePrimitive,
)
from packages.synthetic_motifs.primitives.organic import (
    MedallionPrimitive,
    NichePrimitive,
    PalmettePrimitive,
    LotusPrimitive,
    VineScrollPrimitive,
    CloudBandPrimitive,
    TreePrimitive,
    HornPrimitive,
    HumanFigurePrimitive,
)
from packages.synthetic_motifs.primitives.unmapped import UnmappedMotifPrimitive


class VisualCandidateKey(str, Enum):
    CLOUD_BAND_LIKE = "cloud_band_like"
    COMB_LIKE = "comb_like"
    HOOK_LIKE = "hook_like"
    HORN_LIKE = "horn_like"
    HUMAN_FIGURE_LIKE_GEOMETRIC = "human_figure_like_geometric"
    LATTICE_LIKE = "lattice_like"
    LOTUS_LIKE = "lotus_like"
    LOZENGE_LIKE = "lozenge_like"
    MEDALLION_LIKE = "medallion_like"
    NICHE_LIKE = "niche_like"
    OCTAGONAL_FORM = "octagonal_form"
    PALMETTE_LIKE = "palmette_like"
    ROSETTE_LIKE = "rosette_like"
    STAR_LIKE = "star_like"
    TREE_LIKE = "tree_like"
    UNMAPPED_VISUAL_MOTIF = "unmapped_visual_motif"
    VINE_SCROLL_LIKE = "vine_scroll_like"


@dataclass(frozen=True)
class MotifRegistryEntry:
    visual_candidate_key: VisualCandidateKey
    primitive_cls: Any
    geometry_family: str
    supports_rotation: bool
    supports_repetition: bool
    supports_polygon_gt: bool
    supports_obb_gt: bool
    minimum_scale: float
    maximum_scale: float
    default_parameters: Dict[str, Any]
    registry_version: str = "synthetic-motif-registry-v1.0.0"


class SyntheticMotifRegistry:
    """Canonical registry containing all 17 procedural motif definitions."""

    def __init__(self):
        self._entries: Dict[VisualCandidateKey, MotifRegistryEntry] = {
            VisualCandidateKey.MEDALLION_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.MEDALLION_LIKE,
                primitive_cls=MedallionPrimitive,
                geometry_family="composition_radial",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.15,
                maximum_scale=0.85,
                default_parameters={"lobe_count": 8, "pointedness": 0.4, "aspect_ratio": 1.0, "pendant_style": "diamond"},
            ),
            VisualCandidateKey.NICHE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.NICHE_LIKE,
                primitive_cls=NichePrimitive,
                geometry_family="architectural_arch",
                supports_rotation=False,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.25,
                maximum_scale=0.90,
                default_parameters={"arch_type": "pointed", "steepness": 0.5, "column_width": 0.12},
            ),
            VisualCandidateKey.STAR_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.STAR_LIKE,
                primitive_cls=StarPrimitive,
                geometry_family="geometric_radial",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.08,
                maximum_scale=0.60,
                default_parameters={"points": 8, "inner_radius_ratio": 0.5, "stepped_edges": False},
            ),
            VisualCandidateKey.ROSETTE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.ROSETTE_LIKE,
                primitive_cls=RosettePrimitive,
                geometry_family="organic_radial",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.08,
                maximum_scale=0.50,
                default_parameters={"petal_count": 8, "petal_roundness": 0.6},
            ),
            VisualCandidateKey.PALMETTE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.PALMETTE_LIKE,
                primitive_cls=PalmettePrimitive,
                geometry_family="organic_fan",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.10,
                maximum_scale=0.60,
                default_parameters={"lobe_count": 5, "flare_angle": 80.0},
            ),
            VisualCandidateKey.LOTUS_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.LOTUS_LIKE,
                primitive_cls=LotusPrimitive,
                geometry_family="organic_cup",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.08,
                maximum_scale=0.50,
                default_parameters={"tier_count": 3, "cup_spread": 0.65, "pointedness": 0.5},
            ),
            VisualCandidateKey.VINE_SCROLL_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.VINE_SCROLL_LIKE,
                primitive_cls=VineScrollPrimitive,
                geometry_family="organic_scroll",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.10,
                maximum_scale=0.70,
                default_parameters={"spiral_turns": 1.25, "leaf_density": 4, "stroke_width": 0.04},
            ),
            VisualCandidateKey.CLOUD_BAND_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.CLOUD_BAND_LIKE,
                primitive_cls=CloudBandPrimitive,
                geometry_family="organic_ribbon",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.12,
                maximum_scale=0.65,
                default_parameters={"undulation_count": 3, "curl_radius": 0.25, "ribbon_thickness": 0.08},
            ),
            VisualCandidateKey.TREE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.TREE_LIKE,
                primitive_cls=TreePrimitive,
                geometry_family="organic_branching",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.15,
                maximum_scale=0.80,
                default_parameters={"branch_pairs": 4, "branch_angle": 45.0, "crown_style": "cypress_tapered"},
            ),
            VisualCandidateKey.HORN_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.HORN_LIKE,
                primitive_cls=HornPrimitive,
                geometry_family="geometric_curvilinear",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.08,
                maximum_scale=0.50,
                default_parameters={"curl_direction": "opposing_outward", "spiral_depth": 0.8, "stem_height": 0.3},
            ),
            VisualCandidateKey.HUMAN_FIGURE_LIKE_GEOMETRIC: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.HUMAN_FIGURE_LIKE_GEOMETRIC,
                primitive_cls=HumanFigurePrimitive,
                geometry_family="geometric_stylized_figurative",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.10,
                maximum_scale=0.55,
                default_parameters={"arm_pose": "hands_on_hips", "skirt_style": "triangular", "head_form": "diamond"},
            ),
            VisualCandidateKey.COMB_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.COMB_LIKE,
                primitive_cls=CombPrimitive,
                geometry_family="geometric_linear",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.06,
                maximum_scale=0.40,
                default_parameters={"tooth_count": 5, "spine_thickness": 0.2, "tooth_spacing": 0.15},
            ),
            VisualCandidateKey.HOOK_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.HOOK_LIKE,
                primitive_cls=HookPrimitive,
                geometry_family="geometric_polyline",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.05,
                maximum_scale=0.40,
                default_parameters={"hook_steps": 2, "orientation": "cw", "thickness": 0.15},
            ),
            VisualCandidateKey.LATTICE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.LATTICE_LIKE,
                primitive_cls=LatticePrimitive,
                geometry_family="composition_grid",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.20,
                maximum_scale=0.90,
                default_parameters={"cell_rows": 3, "cell_cols": 3, "strut_width": 0.04},
            ),
            VisualCandidateKey.LOZENGE_LIKE: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.LOZENGE_LIKE,
                primitive_cls=LozengePrimitive,
                geometry_family="geometric_polygon",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.08,
                maximum_scale=0.60,
                default_parameters={"stepped_levels": 1, "aspect_ratio": 1.2},
            ),
            VisualCandidateKey.OCTAGONAL_FORM: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.OCTAGONAL_FORM,
                primitive_cls=OctagonPrimitive,
                geometry_family="geometric_polygon",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.10,
                maximum_scale=0.70,
                default_parameters={"step_style": "regular", "aspect_ratio": 1.0},
            ),
            VisualCandidateKey.UNMAPPED_VISUAL_MOTIF: MotifRegistryEntry(
                visual_candidate_key=VisualCandidateKey.UNMAPPED_VISUAL_MOTIF,
                primitive_cls=UnmappedMotifPrimitive,
                geometry_family="abstract_glyph",
                supports_rotation=True,
                supports_repetition=True,
                supports_polygon_gt=True,
                supports_obb_gt=True,
                minimum_scale=0.06,
                maximum_scale=0.45,
                default_parameters={"glyph_seed": 1, "complexity": 5},
            ),
        }

    def get(self, key: Any) -> MotifRegistryEntry:
        if isinstance(key, str):
            try:
                key = VisualCandidateKey(key)
            except ValueError:
                pass
        if key not in self._entries:
            raise KeyError(f"Visual candidate key '{key}' not found in registry.")
        return self._entries[key]

    def list_keys(self) -> List[VisualCandidateKey]:
        return list(self._entries.keys())

    def list_entries(self) -> List[MotifRegistryEntry]:
        return list(self._entries.values())

    def generate_polygon(
        self,
        key: VisualCandidateKey,
        cx: float,
        cy: float,
        radius: float,
        params: Optional[Dict[str, Any]] = None,
        rotation_deg: float = 0.0,
    ) -> Polygon:
        entry = self.get(key)
        merged_params = dict(entry.default_parameters)
        if params:
            merged_params.update(params)
        merged_params["cx"] = cx
        merged_params["cy"] = cy
        merged_params["radius"] = radius
        merged_params["rotation_deg"] = rotation_deg
        return entry.primitive_cls.generate(**merged_params)
