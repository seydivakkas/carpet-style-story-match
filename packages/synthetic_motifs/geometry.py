"""
Computational Geometry and Vector Mathematics for Synthetic Motifs.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Sequence
import math
import numpy as np
import cv2


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_list(self) -> List[float]:
        return [self.x, self.y]


@dataclass
class BoundingBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def to_xyxy(self) -> List[float]:
        return [float(self.xmin), float(self.ymin), float(self.xmax), float(self.ymax)]

    def to_normalized(self, width: float, height: float) -> List[float]:
        w = max(width, 1.0)
        h = max(height, 1.0)
        return [
            float(np.clip(self.xmin / w, 0.0, 1.0)),
            float(np.clip(self.ymin / h, 0.0, 1.0)),
            float(np.clip(self.xmax / w, 0.0, 1.0)),
            float(np.clip(self.ymax / h, 0.0, 1.0)),
        ]

    def to_yolo_detect(self, width: float, height: float) -> Tuple[float, float, float, float]:
        norm = self.to_normalized(width, height)
        xmin, ymin, xmax, ymax = norm
        w = max(xmax - xmin, 0.0)
        h = max(ymax - ymin, 0.0)
        xc = xmin + w / 2.0
        yc = ymin + h / 2.0
        return (float(xc), float(yc), float(w), float(h))

    @property
    def area(self) -> float:
        return max(0.0, self.xmax - self.xmin) * max(0.0, self.ymax - self.ymin)

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)


@dataclass
class OrientedBoundingBox:
    """Four-corner 2D Oriented Bounding Box representation [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]."""
    corners: List[Tuple[float, float]]

    def to_list(self) -> List[List[float]]:
        return [[float(p[0]), float(p[1])] for p in self.corners]

    def to_normalized(self, width: float, height: float) -> List[List[float]]:
        w = max(width, 1.0)
        h = max(height, 1.0)
        return [
            [
                float(np.clip(p[0] / w, 0.0, 1.0)),
                float(np.clip(p[1] / h, 0.0, 1.0)),
            ]
            for p in self.corners
        ]

    def to_yolo_obb(self, width: float, height: float) -> List[float]:
        """Returns 8 normalized floats: x1, y1, x2, y2, x3, y3, x4, y4."""
        norm = self.to_normalized(width, height)
        flattened = []
        for p in norm:
            flattened.extend([p[0], p[1]])
        return flattened


class Polygon:
    """2D Polygon representation with computational geometry operations."""

    def __init__(self, vertices: Sequence[Tuple[float, float]]):
        if len(vertices) < 3:
            raise ValueError("A polygon must have at least 3 vertices.")
        self.vertices: List[Tuple[float, float]] = [(float(v[0]), float(v[1])) for v in vertices]

    def to_list(self) -> List[List[float]]:
        return [[float(v[0]), float(v[1])] for v in self.vertices]

    def to_normalized(self, width: float, height: float) -> List[List[float]]:
        w = max(width, 1.0)
        h = max(height, 1.0)
        return [
            [
                float(np.clip(v[0] / w, 0.0, 1.0)),
                float(np.clip(v[1] / h, 0.0, 1.0)),
            ]
            for v in self.vertices
        ]

    def to_yolo_segment(self, width: float, height: float) -> List[float]:
        """Returns normalized coordinates [x1, y1, x2, y2, ...]."""
        norm = self.to_normalized(width, height)
        flat = []
        for p in norm:
            flat.extend([p[0], p[1]])
        return flat

    @property
    def area(self) -> float:
        """Computes polygon area using the Shoelace formula."""
        n = len(self.vertices)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i][0] * self.vertices[j][1]
            area -= self.vertices[j][0] * self.vertices[i][1]
        return abs(area) / 2.0

    @property
    def centroid(self) -> Tuple[float, float]:
        """Computes polygon centroid (cx, cy)."""
        n = len(self.vertices)
        if n < 3:
            return (0.0, 0.0)
        cx, cy = 0.0, 0.0
        signed_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            factor = self.vertices[i][0] * self.vertices[j][1] - self.vertices[j][0] * self.vertices[i][1]
            signed_area += factor
            cx += (self.vertices[i][0] + self.vertices[j][0]) * factor
            cy += (self.vertices[i][1] + self.vertices[j][1]) * factor
        if abs(signed_area) < 1e-7:
            # Fallback to mean
            xs = [v[0] for v in self.vertices]
            ys = [v[1] for v in self.vertices]
            return (float(np.mean(xs)), float(np.mean(ys)))
        signed_area *= 0.5
        cx /= (6.0 * signed_area)
        cy /= (6.0 * signed_area)
        return (float(cx), float(cy))

    def get_bounding_box(self) -> BoundingBox:
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        return BoundingBox(
            xmin=float(min(xs)),
            ymin=float(min(ys)),
            xmax=float(max(xs)),
            ymax=float(max(ys)),
        )

    def get_oriented_bounding_box(self) -> OrientedBoundingBox:
        """Computes exact Minimum Area Bounding Box (OBB) using OpenCV."""
        pts = np.array(self.vertices, dtype=np.float32)
        rect = cv2.minAreaRect(pts)
        box = cv2.boxPoints(rect)  # 4x2 array
        # Order corners deterministically: top-left, top-right, bottom-right, bottom-left
        corners = [(float(p[0]), float(p[1])) for p in box]
        return OrientedBoundingBox(corners=corners)

    def transform_affine(self, matrix_2x3: np.ndarray) -> "Polygon":
        """Applies 2x3 affine transformation matrix [a, b, tx; c, d, ty]."""
        pts = np.array(self.vertices, dtype=np.float32)
        ones = np.ones((len(pts), 1), dtype=np.float32)
        homo = np.hstack([pts, ones])
        transformed = (matrix_2x3 @ homo.T).T
        return Polygon([(float(p[0]), float(p[1])) for p in transformed])

    def transform_homography(self, H_3x3: np.ndarray) -> "Polygon":
        """Applies 3x3 projective homography transformation matrix."""
        pts = np.array(self.vertices, dtype=np.float32)
        ones = np.ones((len(pts), 1), dtype=np.float32)
        homo = np.hstack([pts, ones])  # Nx3
        projected = (H_3x3 @ homo.T).T  # Nx3
        # Normalize by w (3rd coordinate)
        w = projected[:, 2:3]
        w[np.abs(w) < 1e-8] = 1e-8
        pts_warp = projected[:, :2] / w
        return Polygon([(float(p[0]), float(p[1])) for p in pts_warp])

    def clip_to_canvas(self, width: float, height: float) -> Optional["Polygon"]:
        """Clips polygon to axis-aligned canvas [0, width] x [0, height] using Sutherland-Hodgman algorithm."""
        output_list = list(self.vertices)
        
        # 4 clip edges: left (x>=0), right (x<=W), top (y>=0), bottom (y<=H)
        clip_edges = [
            ("left", lambda p: p[0] >= 0.0, 0.0, True),
            ("right", lambda p: p[0] <= width, width, True),
            ("top", lambda p: p[1] >= 0.0, 0.0, False),
            ("bottom", lambda p: p[1] <= height, height, False),
        ]

        for edge_name, inside_fn, boundary_val, is_x in clip_edges:
            input_list = output_list
            output_list = []
            if not input_list:
                break
            
            s = input_list[-1]
            for e in input_list:
                if inside_fn(e):
                    if inside_fn(s):
                        output_list.append(e)
                    else:
                        inter = self._intersect(s, e, boundary_val, is_x)
                        if inter:
                            output_list.append(inter)
                        output_list.append(e)
                elif inside_fn(s):
                    inter = self._intersect(s, e, boundary_val, is_x)
                    if inter:
                        output_list.append(inter)
                s = e

        if len(output_list) < 3:
            return None
        
        p = Polygon(output_list)
        if p.area < 1e-3:
            return None
        return p

    @staticmethod
    def _intersect(p1: Tuple[float, float], p2: Tuple[float, float], val: float, is_x: bool) -> Optional[Tuple[float, float]]:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        if is_x:
            if abs(dx) < 1e-8:
                return None
            t = (val - p1[0]) / dx
            return (val, float(p1[1] + t * dy))
        else:
            if abs(dy) < 1e-8:
                return None
            t = (val - p1[1]) / dy
            return (float(p1[0] + t * dx), val)


def create_homography_matrix(
    src_corners: Sequence[Tuple[float, float]],
    dst_corners: Sequence[Tuple[float, float]]
) -> np.ndarray:
    """Computes exact 3x3 homography matrix from 4 source points to 4 destination points."""
    src = np.array(src_corners, dtype=np.float32)
    dst = np.array(dst_corners, dtype=np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    return H.astype(np.float64)
