"""
Organic and Architectural Vector Motif Primitives.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from packages.synthetic_motifs.geometry import Polygon


class MedallionPrimitive:
    """Parametric medallion polygon generator with lobing, pointed tips, and pendants."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        lobe_count: int = 8,
        pointedness: float = 0.4,
        aspect_ratio: float = 1.0,
        pendant_style: str = "diamond",
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        vertices: List[Tuple[float, float]] = []
        samples_per_lobe = 12
        total_samples = lobe_count * samples_per_lobe
        rot_rad = math.radians(rotation_deg)

        for i in range(total_samples):
            angle = (i * 2.0 * math.pi / total_samples) + rot_rad
            # Lobe radius modulation
            phase = (i % samples_per_lobe) / float(samples_per_lobe) * math.pi
            r_base = radius * (1.0 - pointedness * (1.0 - math.sin(phase)))
            
            # Add top/bottom pendant elongation if aligned
            if pendant_style != "none":
                # Check closeness to vertical axes (angle ~ +/- pi/2)
                vert_dist = min(abs(math.sin(angle) - 1.0), abs(math.sin(angle) + 1.0))
                if vert_dist < 0.15:
                    r_base *= (1.0 + (0.15 - vert_dist) * 1.5)

            x = cx + r_base * math.cos(angle) * aspect_ratio
            y = cy + r_base * math.sin(angle)
            vertices.append((x, y))

        return Polygon(vertices)


class NichePrimitive:
    """Parametric architectural arch / niche polygon generator."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        arch_type: str = "pointed",
        steepness: float = 0.5,
        column_width: float = 0.12,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        w = radius * 1.4
        h = radius * 1.8
        cw = w * column_width
        rot_rad = math.radians(rotation_deg)

        raw_pts: List[Tuple[float, float]] = []
        
        # Arch apex at top (0, -h/2)
        # Columns on left and right
        raw_pts.append((-w / 2.0, h / 2.0))  # bottom-left
        raw_pts.append((-w / 2.0 + cw, h / 2.0))  # inner bottom-left
        raw_pts.append((-w / 2.0 + cw, 0.0))  # inner arch spring left
        
        # Arch curve up to apex
        n_arch_pts = 10
        if arch_type == "stepped":
            for s in range(5):
                t = s / 5.0
                ax = (-w / 2.0 + cw) * (1.0 - t)
                ay = -h * 0.4 * t
                raw_pts.append((ax, ay))
            raw_pts.append((0.0, -h / 2.0))
            for s in range(4, -1, -1):
                t = s / 5.0
                ax = (w / 2.0 - cw) * (1.0 - t)
                ay = -h * 0.4 * t
                raw_pts.append((ax, ay))
        else:
            # Pointed arch curve
            for i in range(n_arch_pts):
                t = i / float(n_arch_pts - 1)
                ang = math.pi + t * (math.pi / 2.0)
                ax = (-w / 2.0 + cw) * math.cos(t * (math.pi / 2.0))
                ay = -h * (0.1 + steepness * 0.4) * math.sin(t * (math.pi / 2.0))
                raw_pts.append((ax, ay))
            for i in range(n_arch_pts - 1, -1, -1):
                t = i / float(n_arch_pts - 1)
                ax = (w / 2.0 - cw) * math.cos(t * (math.pi / 2.0))
                ay = -h * (0.1 + steepness * 0.4) * math.sin(t * (math.pi / 2.0))
                raw_pts.append((ax, ay))

        raw_pts.append((w / 2.0 - cw, 0.0))  # inner arch spring right
        raw_pts.append((w / 2.0 - cw, h / 2.0))  # inner bottom-right
        raw_pts.append((w / 2.0, h / 2.0))  # outer bottom-right
        raw_pts.append((w / 2.0, -h / 2.0))  # outer top-right
        raw_pts.append((-w / 2.0, -h / 2.0))  # outer top-left

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class PalmettePrimitive:
    """Parametric fan-shaped palmette with radiating lobes and calyx."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        lobe_count: int = 5,
        flare_angle: float = 80.0,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        half_flare = math.radians(flare_angle / 2.0)
        n_lobes = max(3, lobe_count)

        # Base stem at bottom
        stem_w = radius * 0.15
        stem_h = radius * 0.3
        raw_pts.append((-stem_w, stem_h))
        raw_pts.append((-stem_w, 0.0))

        # Radiating lobes from left to right
        for l in range(n_lobes):
            t = l / float(n_lobes - 1)
            ang = -math.pi / 2.0 - half_flare + t * (2.0 * half_flare)
            # Center lobe is longest
            center_factor = 1.0 - 0.35 * abs(t - 0.5) * 2.0
            r_lobe = radius * center_factor
            
            # Left side of lobe
            raw_pts.append((
                (r_lobe * 0.7) * math.cos(ang - 0.1),
                (r_lobe * 0.7) * math.sin(ang - 0.1)
            ))
            # Tip of lobe
            raw_pts.append((
                r_lobe * math.cos(ang),
                r_lobe * math.sin(ang)
            ))
            # Right side of lobe
            raw_pts.append((
                (r_lobe * 0.7) * math.cos(ang + 0.1),
                (r_lobe * 0.7) * math.sin(ang + 0.1)
            ))

        raw_pts.append((stem_w, 0.0))
        raw_pts.append((stem_w, stem_h))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class LotusPrimitive:
    """Parametric lotus flower polygon with tiered pointed cup petals."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        tier_count: int = 3,
        cup_spread: float = 0.65,
        pointedness: float = 0.5,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        w = radius * cup_spread * 1.5
        h = radius * 1.2

        # Base calyx
        raw_pts.append((0.0, h / 2.0))
        raw_pts.append((-w * 0.3, h * 0.3))

        # Outer left petal
        raw_pts.append((-w * 0.6, 0.0))
        raw_pts.append((-w * 0.5, -h * 0.3))
        # Inner left petal
        raw_pts.append((-w * 0.25, -h * 0.45))
        # Central main apex
        raw_pts.append((0.0, -h / 2.0))
        # Inner right petal
        raw_pts.append((w * 0.25, -h * 0.45))
        # Outer right petal
        raw_pts.append((w * 0.5, -h * 0.3))
        raw_pts.append((w * 0.6, 0.0))

        raw_pts.append((w * 0.3, h * 0.3))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class VineScrollPrimitive:
    """Parametric sinuous vine scroll / spiral with attached curled foliage."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        spiral_turns: float = 1.25,
        leaf_density: int = 4,
        stroke_width: float = 0.04,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        n_pts = 24
        th = radius * stroke_width

        # Outer spiral curve
        for i in range(n_pts):
            t = i / float(n_pts - 1)
            ang = t * (spiral_turns * 2.0 * math.pi)
            r = radius * (0.2 + 0.8 * t)
            raw_pts.append(((r + th) * math.cos(ang), (r + th) * math.sin(ang)))

        # Inner spiral curve backwards
        for i in range(n_pts - 1, -1, -1):
            t = i / float(n_pts - 1)
            ang = t * (spiral_turns * 2.0 * math.pi)
            r = radius * (0.2 + 0.8 * t)
            raw_pts.append(((r - th) * math.cos(ang), (r - th) * math.sin(ang)))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class CloudBandPrimitive:
    """Parametric stylized cloud-band ribbon loop polygon."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        undulation_count: int = 3,
        curl_radius: float = 0.25,
        ribbon_thickness: float = 0.08,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        w = radius * 1.6
        th = radius * ribbon_thickness
        n_samples = 30

        # Top undulating edge
        for i in range(n_samples):
            t = i / float(n_samples - 1)
            x = -w / 2.0 + t * w
            y = radius * 0.3 * math.sin(t * undulation_count * math.pi) - th / 2.0
            raw_pts.append((x, y))

        # Right curl loop
        curl_r = radius * curl_radius
        for a in np.linspace(0, np.pi, 8):
            raw_pts.append((w / 2.0 + curl_r * math.sin(a), y + curl_r * (1.0 - math.cos(a))))

        # Bottom undulating edge backwards
        for i in range(n_samples - 1, -1, -1):
            t = i / float(n_samples - 1)
            x = -w / 2.0 + t * w
            y = radius * 0.3 * math.sin(t * undulation_count * math.pi) + th / 2.0
            raw_pts.append((x, y))

        # Left curl loop
        for a in np.linspace(0, np.pi, 8):
            raw_pts.append((-w / 2.0 - curl_r * math.sin(a), y - curl_r * (1.0 - math.cos(a))))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class TreePrimitive:
    """Parametric vertical branching tree / cypress silhouette polygon."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        branch_pairs: int = 4,
        branch_angle: float = 45.0,
        crown_style: str = "cypress_tapered",
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        h = radius * 1.8
        w = radius * 0.9
        trunk_w = radius * 0.1
        n_pairs = max(2, branch_pairs)

        # Trunk base
        raw_pts.append((-trunk_w, h / 2.0))
        raw_pts.append((-trunk_w, h * 0.35))

        # Left branches going up
        for b in range(n_pairs):
            t = b / float(n_pairs)
            by = h * 0.35 - t * (h * 0.75)
            bw = w * 0.5 * (1.0 - t * 0.7)
            raw_pts.append((-trunk_w, by))
            raw_pts.append((-bw, by - h * 0.08))
            raw_pts.append((-trunk_w * 0.8, by - h * 0.05))

        # Tree apex
        raw_pts.append((0.0, -h / 2.0))

        # Right branches going down
        for b in range(n_pairs - 1, -1, -1):
            t = b / float(n_pairs)
            by = h * 0.35 - t * (h * 0.75)
            bw = w * 0.5 * (1.0 - t * 0.7)
            raw_pts.append((trunk_w * 0.8, by - h * 0.05))
            raw_pts.append((bw, by - h * 0.08))
            raw_pts.append((trunk_w, by))

        # Trunk base right
        raw_pts.append((trunk_w, h * 0.35))
        raw_pts.append((trunk_w, h / 2.0))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class HornPrimitive:
    """Parametric dual opposing curved spiral horn motif polygon."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        curl_direction: str = "opposing_outward",
        spiral_depth: float = 0.8,
        stem_height: float = 0.3,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        w = radius * 1.4
        h = radius * 1.0

        # Central base stem
        stem_w = radius * 0.12
        raw_pts.append((-stem_w, h / 2.0))
        raw_pts.append((-stem_w, 0.0))

        # Left horn spiral curl
        for a in np.linspace(0, np.pi * 1.5, 12):
            r = radius * 0.4 * (1.0 + (a / (math.pi * 1.5)) * 0.5)
            raw_pts.append((-w * 0.2 - r * math.sin(a), -h * 0.1 - r * math.cos(a)))

        # Bridge apex
        raw_pts.append((0.0, -h * 0.4))

        # Right horn spiral curl
        for a in np.linspace(np.pi * 1.5, 0, 12):
            r = radius * 0.4 * (1.0 + (a / (math.pi * 1.5)) * 0.5)
            raw_pts.append((w * 0.2 + r * math.sin(a), -h * 0.1 - r * math.cos(a)))

        # Stem right
        raw_pts.append((stem_w, 0.0))
        raw_pts.append((stem_w, h / 2.0))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class HumanFigurePrimitive:
    """Parametric stylized geometric human figure (stick torso, limbs, head diamond)."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        arm_pose: str = "hands_on_hips",
        skirt_style: str = "triangular",
        head_form: str = "diamond",
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        raw_pts: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        h = radius * 1.8
        w = radius * 1.1

        # Head (diamond / polygon at top)
        head_r = radius * 0.25
        head_cy = -h / 2.0 + head_r
        raw_pts.append((0.0, -h / 2.0))
        raw_pts.append((head_r, head_cy))
        raw_pts.append((head_r * 0.4, head_cy + head_r * 0.7))

        # Right arm
        if arm_pose == "hands_on_hips":
            raw_pts.append((w / 2.0, head_cy + head_r * 0.8))
            raw_pts.append((w / 2.0 * 0.8, head_cy + head_r * 1.6))
            raw_pts.append((radius * 0.15, head_cy + head_r * 1.5))
        else:
            raw_pts.append((w / 2.0, head_cy + head_r * 0.5))
            raw_pts.append((radius * 0.15, head_cy + head_r * 1.0))

        # Skirt / legs right
        raw_pts.append((w * 0.4, h / 2.0))
        raw_pts.append((0.0, h * 0.35))  # crotch / skirt center
        raw_pts.append((-w * 0.4, h / 2.0))  # skirt left

        # Left arm
        if arm_pose == "hands_on_hips":
            raw_pts.append((-radius * 0.15, head_cy + head_r * 1.5))
            raw_pts.append((-w / 2.0 * 0.8, head_cy + head_r * 1.6))
            raw_pts.append((-w / 2.0, head_cy + head_r * 0.8))
        else:
            raw_pts.append((-radius * 0.15, head_cy + head_r * 1.0))
            raw_pts.append((-w / 2.0, head_cy + head_r * 0.5))

        # Head left
        raw_pts.append((-head_r * 0.4, head_cy + head_r * 0.7))
        raw_pts.append((-head_r, head_cy))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)
