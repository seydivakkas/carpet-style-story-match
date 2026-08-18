"""
Ground Truth Oracle Validation and Geometric Consistency Verification.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import List, Tuple, Dict, Any
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import Polygon, BoundingBox
from packages.synthetic_motifs.annotations import SyntheticMotifInstanceGT


class OracleValidator:
    """Rigorous geometric and annotation oracle verification."""

    @staticmethod
    def verify_mask_bbox_containment(mask: np.ndarray, bbox_xyxy: List[float], margin: float = 2.0) -> bool:
        """Verifies that all non-zero pixels in instance mask lie inside bbox + margin."""
        ys, xs = np.where(mask > 0)
        if len(xs) == 0 or len(ys) == 0:
            return True  # Empty mask trivially contained
        
        mask_xmin = float(np.min(xs))
        mask_xmax = float(np.max(xs))
        mask_ymin = float(np.min(ys))
        mask_ymax = float(np.max(ys))

        xmin, ymin, xmax, ymax = bbox_xyxy
        if mask_xmin < xmin - margin or mask_ymin < ymin - margin:
            return False
        if mask_xmax > xmax + margin or mask_ymax > ymax + margin:
            return False
        return True

    @staticmethod
    def verify_polygon_mask_consistency(polygon: Polygon, mask: np.ndarray, width: int, height: int) -> float:
        """Computes IoU between polygon rasterization and instance mask."""
        poly_mask = np.zeros((height, width), dtype=np.uint8)
        pts = np.array([polygon.vertices], dtype=np.int32)
        cv2.fillPoly(poly_mask, pts, 255)

        intersection = np.logical_and(mask > 0, poly_mask > 0).sum()
        union = np.logical_or(mask > 0, poly_mask > 0).sum()

        if union == 0:
            return 1.0
        return float(intersection / union)

    @staticmethod
    def verify_obb_containment(polygon: Polygon, obb_corners: List[List[float]], margin: float = 1.0) -> bool:
        """Verifies that all polygon vertices lie inside the 4-corner OBB with small tolerance."""
        obb_contour = np.array(obb_corners, dtype=np.float32)
        for pt in polygon.vertices:
            dist = cv2.pointPolygonTest(obb_contour, (float(pt[0]), float(pt[1])), True)
            if dist < -margin:
                return False
        return True

    @staticmethod
    def verify_homography_point_projection(
        src_points: List[Tuple[float, float]],
        H_3x3: np.ndarray,
        dst_points: List[Tuple[float, float]],
        tolerance: float = 1e-4,
    ) -> bool:
        """Verifies that transformed polygon vertices match exact mathematical homography projection."""
        pts = np.array(src_points, dtype=np.float64)
        ones = np.ones((len(pts), 1), dtype=np.float64)
        homo = np.hstack([pts, ones])  # Nx3
        projected = (H_3x3 @ homo.T).T
        w = projected[:, 2:3]
        expected_dst = projected[:, :2] / w
        
        actual_dst = np.array(dst_points, dtype=np.float64)
        diff = np.max(np.abs(expected_dst - actual_dst))
        return bool(diff < tolerance)

    @staticmethod
    def verify_photometric_invariance(
        inst_before: SyntheticMotifInstanceGT,
        inst_after: SyntheticMotifInstanceGT
    ) -> bool:
        """Verifies that photometric distortions do NOT alter geometry ground truth."""
        bbox_match = inst_before.bbox_xyxy == inst_after.bbox_xyxy
        poly_match = inst_before.polygon == inst_after.polygon
        obb_match = inst_before.obb == inst_after.obb
        class_match = inst_before.visual_candidate_key == inst_after.visual_candidate_key
        return bbox_match and poly_match and obb_match and class_match
