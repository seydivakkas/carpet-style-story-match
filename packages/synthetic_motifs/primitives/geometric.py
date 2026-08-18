"""
Geometric Vector Motif Primitives.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from packages.synthetic_motifs.geometry import Polygon


class StarPrimitive:
    """Parametric n-pointed star polygon generator."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        points: int = 8,
        inner_radius_ratio: float = 0.5,
        stepped_edges: bool = False,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        vertices: List[Tuple[float, float]] = []
        r_outer = radius
        r_inner = radius * inner_radius_ratio
        total_angles = points * 2
        rot_rad = math.radians(rotation_deg)

        for i in range(total_angles):
            angle = (i * 2.0 * math.pi / total_angles) + rot_rad
            r = r_outer if i % 2 == 0 else r_inner
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            vertices.append((x, y))

            if stepped_edges and i % 2 == 0:
                # Add a stepped notch halfway to inner
                mid_angle = angle + (math.pi / total_angles) * 0.5
                r_mid = (r_outer + r_inner) * 0.5
                vertices.append((cx + r_mid * math.cos(mid_angle), cy + r_mid * math.sin(mid_angle)))

        return Polygon(vertices)


class OctagonPrimitive:
    """Parametric 8-sided octagon polygon generator with stepped and gul variants."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        step_style: str = "regular",
        aspect_ratio: float = 1.0,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        vertices: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)

        if step_style == "stepped_corners":
            # 16-vertex stepped octagon
            base_angles = np.linspace(0, 2 * np.pi, 9)[:-1]
            for i, ang in enumerate(base_angles):
                # corner step
                a1 = ang - math.pi / 16.0 + rot_rad
                a2 = ang + math.pi / 16.0 + rot_rad
                x1 = cx + radius * math.cos(a1) * aspect_ratio
                y1 = cy + radius * math.sin(a1)
                x2 = cx + radius * math.cos(a2) * aspect_ratio
                y2 = cy + radius * math.sin(a2)
                vertices.extend([(x1, y1), (x2, y2)])
        elif step_style == "gul_lobed":
            # 24-point lobed gul octagon
            for i in range(24):
                ang = (i * 2.0 * math.pi / 24.0) + rot_rad
                r = radius * (0.85 + 0.15 * math.cos(4 * ang))
                x = cx + r * math.cos(ang) * aspect_ratio
                y = cy + r * math.sin(ang)
                vertices.append((x, y))
        else:
            # Regular 8-sided polygon
            for i in range(8):
                ang = (i * 2.0 * math.pi / 8.0) + (math.pi / 8.0) + rot_rad
                x = cx + radius * math.cos(ang) * aspect_ratio
                y = cy + radius * math.sin(ang)
                vertices.append((x, y))

        return Polygon(vertices)


class LozengePrimitive:
    """Parametric lozenge / rhombus polygon with stepped border variants."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        stepped_levels: int = 1,
        aspect_ratio: float = 1.2,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        vertices: List[Tuple[float, float]] = []
        rot_rad = math.radians(rotation_deg)
        rx = radius * aspect_ratio
        ry = radius

        if stepped_levels <= 0:
            # Simple 4-vertex diamond
            raw_pts = [(0, -ry), (rx, 0), (0, ry), (-rx, 0)]
        else:
            # Stepped diamond contour
            raw_pts = []
            steps = stepped_levels + 1
            # Top to Right
            for s in range(steps):
                x = rx * (s / steps)
                y = -ry * (1.0 - s / steps)
                raw_pts.append((x, y))
                if s < steps - 1:
                    raw_pts.append((rx * ((s + 1) / steps), y))
            # Right to Bottom
            for s in range(steps):
                x = rx * (1.0 - s / steps)
                y = ry * (s / steps)
                raw_pts.append((x, y))
                if s < steps - 1:
                    raw_pts.append((x, ry * ((s + 1) / steps)))
            # Bottom to Left
            for s in range(steps):
                x = -rx * (s / steps)
                y = ry * (1.0 - s / steps)
                raw_pts.append((x, y))
                if s < steps - 1:
                    raw_pts.append((-rx * ((s + 1) / steps), y))
            # Left to Top
            for s in range(steps):
                x = -rx * (1.0 - s / steps)
                y = -ry * (s / steps)
                raw_pts.append((x, y))
                if s < steps - 1:
                    raw_pts.append((x, -ry * ((s + 1) / steps)))

        # Rotate around (cx, cy)
        for px, py in raw_pts:
            rx_rot = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry_rot = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx_rot, ry_rot))

        return Polygon(vertices)


class RosettePrimitive:
    """Parametric circular multi-petal rosette polygon."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        petal_count: int = 8,
        petal_roundness: float = 0.6,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        vertices: List[Tuple[float, float]] = []
        samples_per_petal = 8
        total_samples = petal_count * samples_per_petal
        rot_rad = math.radians(rotation_deg)

        for i in range(total_samples):
            angle = (i * 2.0 * math.pi / total_samples) + rot_rad
            # Radial modulation creating rounded petals
            petal_phase = (i % samples_per_petal) / float(samples_per_petal) * math.pi
            r_mod = radius * (1.0 - (1.0 - petal_roundness) * (1.0 - math.sin(petal_phase)))
            x = cx + r_mod * math.cos(angle)
            y = cy + r_mod * math.sin(angle)
            vertices.append((x, y))

        return Polygon(vertices)


class CombPrimitive:
    """Parametric comb-like geometric motif with spine and parallel teeth."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        tooth_count: int = 5,
        spine_thickness: float = 0.2,
        tooth_spacing: float = 0.15,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        w = radius * 1.5
        h = radius * 1.0
        spine_h = h * spine_thickness
        tooth_h = h - spine_h
        n_teeth = max(2, tooth_count)

        raw_pts: List[Tuple[float, float]] = []
        # Spine top edge (left to right)
        raw_pts.append((-w / 2.0, -h / 2.0))
        raw_pts.append((w / 2.0, -h / 2.0))
        raw_pts.append((w / 2.0, -h / 2.0 + spine_h))

        # Teeth along bottom of spine (right to left)
        tooth_w = (w / n_teeth) * 0.5
        gap_w = (w / n_teeth) * 0.5
        for t in range(n_teeth - 1, -1, -1):
            tx_start = -w / 2.0 + t * (tooth_w + gap_w)
            tx_end = tx_start + tooth_w
            # Right side of tooth
            raw_pts.append((tx_end, -h / 2.0 + spine_h))
            raw_pts.append((tx_end, h / 2.0))
            raw_pts.append((tx_start, h / 2.0))
            raw_pts.append((tx_start, -h / 2.0 + spine_h))

        raw_pts.append((-w / 2.0, -h / 2.0 + spine_h))

        # Rotate and translate
        rot_rad = math.radians(rotation_deg)
        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class HookPrimitive:
    """Parametric latch-hook / stepped hook geometric polygon."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        hook_steps: int = 2,
        orientation: str = "cw",
        thickness: float = 0.15,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        w = radius * 1.2
        h = radius * 1.2
        th = radius * max(0.08, thickness)
        
        # Spiral-stepped hook boundary
        raw_pts: List[Tuple[float, float]] = [
            (-w / 2.0, -h / 2.0),
            (w / 2.0, -h / 2.0),
            (w / 2.0, h / 2.0),
            (w / 2.0 - th, h / 2.0),
            (w / 2.0 - th, -h / 2.0 + th),
            (0.0, -h / 2.0 + th),
            (0.0, 0.0),
            (-th, 0.0),
            (-th, -h / 2.0 + th),
            (-w / 2.0, -h / 2.0 + th),
        ]

        if orientation == "ccw":
            raw_pts = [(-x, y) for x, y in raw_pts]

        rot_rad = math.radians(rotation_deg)
        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)


class LatticePrimitive:
    """Parametric intersecting diamond/rhombus lattice grid mesh boundary."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        cell_rows: int = 3,
        cell_cols: int = 3,
        strut_width: float = 0.04,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        # Generate the outer lattice boundary polygon
        w = radius * 1.5
        h = radius * 1.5
        rot_rad = math.radians(rotation_deg)

        # 8-point faceted diamond-boundary for the lattice cluster
        raw_pts = [
            (0, -h / 2.0),
            (w / 4.0, -h / 4.0),
            (w / 2.0, 0),
            (w / 4.0, h / 4.0),
            (0, h / 2.0),
            (-w / 4.0, h / 4.0),
            (-w / 2.0, 0),
            (-w / 4.0, -h / 4.0),
        ]

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)
