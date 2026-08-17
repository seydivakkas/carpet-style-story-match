"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Deterministic Color Extractor.
Uses CIELAB K-Means clustering, small cluster suppression, near-color merging,
and perceptual labeling to compute ColorObservation lists.
"""
import io
import math
import numpy as np
import cv2
from PIL import Image
from typing import List, Tuple, Dict, Any

from app.domain.color_analysis.models import ColorObservation, COLOR_OBSERVATION_SCHEMA_VERSION
from app.domain.color_analysis.labels import get_nearest_perceptual_label

COLOR_ANALYSIS_MAX_SIDE = 512


class ColorExtractor:
    """Deterministic K-Means Color Extraction in CIELAB space."""

    def __init__(
        self,
        min_k: int = 3,
        max_k: int = 8,
        default_k: int = 5,
        min_coverage: float = 0.015,
        merge_delta_e: float = 15.0
    ):
        self.min_k = min_k
        self.max_k = max_k
        self.default_k = default_k
        self.min_coverage = min_coverage
        self.merge_delta_e = merge_delta_e

    def extract_colors(self, raw_bytes: bytes, k: int = 5) -> List[ColorObservation]:
        k = max(self.min_k, min(self.max_k, k))

        # Decode image
        nparr = np.frombuffer(raw_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            try:
                pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ValueError(f"Could not decode image for color extraction: {e}")

        h, w = img_bgr.shape[:2]
        if max(h, w) > COLOR_ANALYSIS_MAX_SIDE:
            scale = COLOR_ANALYSIS_MAX_SIDE / float(max(h, w))
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

        img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        pixels_lab = img_lab.reshape(-1, 3).astype(np.float32)
        pixels_rgb = img_rgb.reshape(-1, 3).astype(np.float32)
        pixels_hsv = img_hsv.reshape(-1, 3).astype(np.float32)

        total_pixels = len(pixels_lab)

        # OpenCV K-Means in CIELAB
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
        _, labels, centers_lab = cv2.kmeans(
            pixels_lab,
            k,
            None,
            criteria,
            10,
            cv2.KMEANS_PP_CENTERS
        )

        labels = labels.flatten()
        cluster_info = []

        for i in range(k):
            mask = (labels == i)
            count = int(np.sum(mask))
            if count == 0:
                continue

            coverage = count / float(total_pixels)
            if coverage < self.min_coverage:
                continue

            c_lab = centers_lab[i]
            c_rgb = np.mean(pixels_rgb[mask], axis=0)
            c_hsv = np.mean(pixels_hsv[mask], axis=0)

            cluster_info.append({
                "lab": [round(float(c_lab[0]), 2), round(float(c_lab[1]), 2), round(float(c_lab[2]), 2)],
                "rgb": [int(round(c_rgb[0])), int(round(c_rgb[1])), int(round(c_rgb[2]))],
                "hsv": [int(round(c_hsv[0])), int(round(c_hsv[1])), int(round(c_hsv[2]))],
                "count": count,
                "coverage": round(coverage, 4)
            })

        # Merge Near Clusters in CIELAB space
        merged_clusters = self._merge_near_clusters(cluster_info, total_pixels)

        # Sort by coverage descending
        merged_clusters.sort(key=lambda x: x["coverage"], reverse=True)

        observations: List[ColorObservation] = []
        for idx, item in enumerate(merged_clusters):
            rgb_list = [max(0, min(255, c)) for c in item["rgb"]]
            hex_code = f"#{rgb_list[0]:02X}{rgb_list[1]:02X}{rgb_list[2]:02X}"
            hsv_list = [max(0, min(255, c)) for c in item["hsv"]]
            lab_list = item["lab"]

            p_label = get_nearest_perceptual_label((lab_list[0], lab_list[1], lab_list[2]))

            obs = ColorObservation(
                color_id=f"color-{idx+1}",
                rgb=rgb_list,
                hex=hex_code,
                hsv=hsv_list,
                lab=lab_list,
                coverage=item["coverage"],
                perceptual_label=p_label,
                region_scope="CANONICAL_CARPET",
                method="kmeans_cielab_v1",
                analysis_version=COLOR_OBSERVATION_SCHEMA_VERSION,
                confidence=0.92,
                dye_material="UNKNOWN"
            )
            observations.append(obs)

        return observations

    def _merge_near_clusters(self, clusters: List[Dict[str, Any]], total_pixels: int) -> List[Dict[str, Any]]:
        """Merges clusters that are closer than merge_delta_e in CIELAB space."""
        if len(clusters) <= 1:
            return clusters

        merged = []
        used = set()

        for i in range(len(clusters)):
            if i in used:
                continue
            c1 = clusters[i]
            lab1 = np.array(c1["lab"])
            rgb_acc = np.array(c1["rgb"], dtype=np.float64) * c1["count"]
            hsv_acc = np.array(c1["hsv"], dtype=np.float64) * c1["count"]
            lab_acc = lab1 * c1["count"]
            total_count = c1["count"]

            for j in range(i + 1, len(clusters)):
                if j in used:
                    continue
                c2 = clusters[j]
                lab2 = np.array(c2["lab"])
                dist = np.linalg.norm(lab1 - lab2)

                if dist < self.merge_delta_e:
                    used.add(j)
                    rgb_acc += np.array(c2["rgb"], dtype=np.float64) * c2["count"]
                    hsv_acc += np.array(c2["hsv"], dtype=np.float64) * c2["count"]
                    lab_acc += lab2 * c2["count"]
                    total_count += c2["count"]

            used.add(i)
            avg_rgb = (rgb_acc / total_count).astype(np.int32).tolist()
            avg_hsv = (hsv_acc / total_count).astype(np.int32).tolist()
            avg_lab = (lab_acc / total_count).tolist()

            merged.append({
                "lab": [round(avg_lab[0], 2), round(avg_lab[1], 2), round(avg_lab[2], 2)],
                "rgb": avg_rgb,
                "hsv": avg_hsv,
                "count": total_count,
                "coverage": round(total_count / float(total_pixels), 4)
            })

        return merged
