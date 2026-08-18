"""
Domain Randomization Engine for Synthetic Carpet Motifs.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import Polygon


class PhotometricRandomizer:
    """Applies appearance-altering photometric adjustments. Does NOT alter geometry."""

    @staticmethod
    def apply(
        image: np.ndarray,
        brightness_range: Tuple[float, float] = (0.8, 1.2),
        contrast_range: Tuple[float, float] = (0.8, 1.2),
        gamma_range: Tuple[float, float] = (0.85, 1.2),
        saturation_range: Tuple[float, float] = (0.7, 1.3),
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        img_float = image.astype(np.float32) / 255.0

        # Brightness & Contrast
        b_factor = float(rng.uniform(brightness_range[0], brightness_range[1]))
        c_factor = float(rng.uniform(contrast_range[0], contrast_range[1]))
        mean = np.mean(img_float, axis=(0, 1), keepdims=True)
        img_float = (img_float - mean) * c_factor + mean
        img_float = img_float * b_factor

        # Gamma
        gamma = float(rng.uniform(gamma_range[0], gamma_range[1]))
        img_float = np.clip(img_float, 0.0, 1.0)
        img_float = np.power(img_float, gamma)

        # Saturation in HSV
        sat_factor = float(rng.uniform(saturation_range[0], saturation_range[1]))
        img_uint8 = np.clip(img_float * 255.0, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_factor, 0, 255)
        out_bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        provenance = {
            "brightness_factor": b_factor,
            "contrast_factor": c_factor,
            "gamma": gamma,
            "saturation_factor": sat_factor,
        }
        return out_bgr, provenance


class ImagingRandomizer:
    """Applies sensor, blur, noise, and compression degradation."""

    @staticmethod
    def apply(
        image: np.ndarray,
        blur_prob: float = 0.4,
        noise_prob: float = 0.5,
        jpeg_quality_range: Tuple[int, int] = (45, 95),
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        out = image.copy()
        applied = {}

        # Gaussian Blur
        if rng.uniform(0, 1) < blur_prob:
            ksize = int(rng.choice([3, 5]))
            sigma = float(rng.uniform(0.5, 1.5))
            out = cv2.GaussianBlur(out, (ksize, ksize), sigma)
            applied["gaussian_blur"] = {"ksize": ksize, "sigma": sigma}

        # Gaussian Noise
        if rng.uniform(0, 1) < noise_prob:
            std = float(rng.uniform(4.0, 14.0))
            noise = rng.normal(0, std, out.shape).astype(np.float32)
            out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            applied["gaussian_noise"] = {"std_dev": std}

        # JPEG Compression Artifacts
        jpeg_quality = int(rng.randint(jpeg_quality_range[0], jpeg_quality_range[1] + 1))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        _, encimg = cv2.imencode(".jpg", out, encode_param)
        out = cv2.imdecode(encimg, 1)
        applied["jpeg_quality"] = jpeg_quality

        return out, applied


class MaterialTextureRandomizer:
    """Procedurally simulates carpet fiber weave texture and low-frequency wear fading."""

    @staticmethod
    def apply(
        image: np.ndarray,
        fiber_amplitude: float = 0.06,
        wear_prob: float = 0.5,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        out_float = image.astype(np.float32)

        # Procedural weave grid texture
        x_coords = np.arange(w)
        y_coords = np.arange(h)
        grid_x = np.sin(x_coords * (2.0 * np.pi / 4.0)) * 0.5 + 0.5
        grid_y = np.cos(y_coords * (2.0 * np.pi / 4.0)) * 0.5 + 0.5
        weave = (grid_x[None, :] * grid_y[:, None] - 0.5) * (fiber_amplitude * 255.0)
        weave_3ch = np.repeat(weave[:, :, None], 3, axis=2)

        out_float = np.clip(out_float + weave_3ch, 0, 255)

        # Wear fading: low frequency noise
        applied_wear = False
        if rng.uniform(0, 1) < wear_prob:
            low_res = rng.uniform(0.85, 1.15, (h // 32 + 1, w // 32 + 1)).astype(np.float32)
            wear_map = cv2.resize(low_res, (w, h), interpolation=cv2.INTER_LINEAR)
            out_float = np.clip(out_float * wear_map[:, :, None], 0, 255)
            applied_wear = True

        return out_float.astype(np.uint8), {"weave_amplitude": fiber_amplitude, "wear_applied": applied_wear}


class OcclusionRandomizer:
    """Generates neutral geometric occluders and computes occlusion masks."""

    @staticmethod
    def apply(
        image: np.ndarray,
        max_occluders: int = 2,
        max_area_fraction: float = 0.08,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, List[Polygon], np.ndarray]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        out = image.copy()
        n_occ = int(rng.randint(1, max_occluders + 1))
        occluder_polys: List[Polygon] = []
        occ_mask = np.zeros((h, w), dtype=np.uint8)

        for _ in range(n_occ):
            cx = float(rng.uniform(w * 0.15, w * 0.85))
            cy = float(rng.uniform(h * 0.15, h * 0.85))
            ow = float(rng.uniform(w * 0.05, w * np.sqrt(max_area_fraction)))
            oh = float(rng.uniform(h * 0.05, h * np.sqrt(max_area_fraction)))
            color = tuple(int(c) for c in rng.randint(40, 220, 3))

            pts = [
                (cx - ow / 2, cy - oh / 2),
                (cx + ow / 2, cy - oh / 2),
                (cx + ow / 2, cy + oh / 2),
                (cx - ow / 2, cy + oh / 2),
            ]
            poly = Polygon(pts)
            occluder_polys.append(poly)

            pts_arr = np.array([pts], dtype=np.int32)
            cv2.fillPoly(out, pts_arr, color, lineType=cv2.LINE_AA)
            cv2.fillPoly(occ_mask, pts_arr, 255)

        return out, occluder_polys, occ_mask
