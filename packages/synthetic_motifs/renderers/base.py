"""
Vector-to-Raster Rendering and Instance Mask Engine.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import Tuple, Optional
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import Polygon


class VectorRenderer:
    """Renders 2D vector polygons onto NumPy RGB canvas and produces exact binary instance masks."""

    @staticmethod
    def create_canvas(width: int, height: int, background_rgb: Tuple[int, int, int] = (240, 235, 220)) -> np.ndarray:
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        canvas[:, :] = background_rgb
        return canvas

    @staticmethod
    def render_polygon_fill(
        canvas: np.ndarray,
        polygon: Polygon,
        fill_rgb: Tuple[int, int, int],
        alpha: float = 1.0,
    ) -> np.ndarray:
        """Renders filled polygon with anti-aliasing onto canvas."""
        pts = np.array([polygon.vertices], dtype=np.int32)
        if alpha >= 0.99:
            cv2.fillPoly(canvas, pts, fill_rgb, lineType=cv2.LINE_AA)
        else:
            overlay = canvas.copy()
            cv2.fillPoly(overlay, pts, fill_rgb, lineType=cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0, canvas)
        return canvas

    @staticmethod
    def render_polygon_stroke(
        canvas: np.ndarray,
        polygon: Polygon,
        stroke_rgb: Tuple[int, int, int],
        thickness: int = 2,
    ) -> np.ndarray:
        """Renders polygon outline onto canvas."""
        pts = np.array([polygon.vertices], dtype=np.int32)
        cv2.polylines(canvas, pts, isClosed=True, color=stroke_rgb, thickness=thickness, lineType=cv2.LINE_AA)
        return canvas

    @staticmethod
    def generate_instance_mask(
        width: int,
        height: int,
        polygon: Polygon,
    ) -> np.ndarray:
        """Generates a binary 2D mask (uint8: 0 or 255) for the given polygon."""
        mask = np.zeros((height, width), dtype=np.uint8)
        pts = np.array([polygon.vertices], dtype=np.int32)
        cv2.fillPoly(mask, pts, 255)
        return mask
