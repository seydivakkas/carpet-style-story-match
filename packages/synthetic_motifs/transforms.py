"""
Geometric Transformations and Exact Ground Truth Projection Engine.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import List, Tuple, Dict, Any, Optional
import math
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import (
    Polygon,
    BoundingBox,
    OrientedBoundingBox,
    create_homography_matrix,
)


class GeometricTransformer:
    """Applies coupled geometric augmentations to raster images and exact vector polygons."""

    @staticmethod
    def apply_perspective(
        image: np.ndarray,
        polygons: List[Polygon],
        max_distortion: float = 0.15,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, List[Optional[Polygon]], np.ndarray, Dict[str, Any]]:
        """Applies homography perspective warp to image and exact projective transform to polygons."""
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        dw = w * max_distortion
        dh = h * max_distortion

        src_corners = [(0.0, 0.0), (float(w), 0.0), (float(w), float(h)), (0.0, float(h))]
        
        # Jitter corners
        dst_corners = [
            (float(rng.uniform(0, dw)), float(rng.uniform(0, dh))),
            (float(w - rng.uniform(0, dw)), float(rng.uniform(0, dh))),
            (float(w - rng.uniform(0, dw)), float(h - rng.uniform(0, dh))),
            (float(rng.uniform(0, dw)), float(h - rng.uniform(0, dh))),
        ]

        H = create_homography_matrix(src_corners, dst_corners)
        
        # Warp image
        warped_img = cv2.warpPerspective(image, H, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        # Warp polygons
        warped_polys: List[Optional[Polygon]] = []
        for poly in polygons:
            try:
                p_warp = poly.transform_homography(H)
                p_clipped = p_warp.clip_to_canvas(float(w), float(h))
                warped_polys.append(p_clipped)
            except Exception:
                warped_polys.append(None)

        provenance = {
            "type": "perspective_homography",
            "homography_matrix": H.tolist(),
            "dst_corners": dst_corners,
        }

        return warped_img, warped_polys, H, provenance

    @staticmethod
    def apply_affine_jitter(
        image: np.ndarray,
        polygons: List[Polygon],
        scale_range: Tuple[float, float] = (0.85, 1.15),
        rotation_deg_range: Tuple[float, float] = (-15.0, 15.0),
        translation_fraction: float = 0.08,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, List[Optional[Polygon]], np.ndarray, Dict[str, Any]]:
        """Applies coupled 2D affine rotation/scale/translation to image and polygons."""
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)
        
        angle = float(rng.uniform(rotation_deg_range[0], rotation_deg_range[1]))
        scale = float(rng.uniform(scale_range[0], scale_range[1]))
        tx = float(rng.uniform(-w * translation_fraction, w * translation_fraction))
        ty = float(rng.uniform(-h * translation_fraction, h * translation_fraction))

        M = cv2.getRotationMatrix2D(center, angle, scale)
        M[0, 2] += tx
        M[1, 2] += ty

        warped_img = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        warped_polys: List[Optional[Polygon]] = []
        for poly in polygons:
            try:
                p_affine = poly.transform_affine(M)
                p_clipped = p_affine.clip_to_canvas(float(w), float(h))
                warped_polys.append(p_clipped)
            except Exception:
                warped_polys.append(None)

        provenance = {
            "type": "affine_jitter",
            "matrix_2x3": M.tolist(),
            "angle_deg": angle,
            "scale": scale,
            "tx": tx,
            "ty": ty,
        }

        return warped_img, warped_polys, M, provenance
