"""
Abstract Glyph Vector Primitive for Unmapped Visual Motifs.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import math
from typing import List, Tuple, Dict, Any
import numpy as np

from packages.synthetic_motifs.geometry import Polygon


class UnmappedMotifPrimitive:
    """Controlled abstract geometric glyph generator for unmapped visual motif candidates."""

    @staticmethod
    def generate(
        cx: float,
        cy: float,
        radius: float,
        glyph_seed: int = 1,
        complexity: int = 5,
        rotation_deg: float = 0.0,
        **kwargs: Any
    ) -> Polygon:
        rng = np.random.RandomState(int(glyph_seed) % (2**31 - 1))
        rot_rad = math.radians(rotation_deg)
        n_pts = max(4, int(complexity) + 2)

        # Generate star-like or faceted convex/concave non-standard glyph contour
        angles = np.sort(rng.uniform(0, 2 * np.pi, n_pts))
        radii = rng.uniform(radius * 0.35, radius, n_pts)

        raw_pts: List[Tuple[float, float]] = []
        for ang, r in zip(angles, radii):
            raw_pts.append((r * math.cos(ang), r * math.sin(ang)))

        vertices = []
        for px, py in raw_pts:
            rx = px * math.cos(rot_rad) - py * math.sin(rot_rad) + cx
            ry = px * math.sin(rot_rad) + py * math.cos(rot_rad) + cy
            vertices.append((rx, ry))

        return Polygon(vertices)
