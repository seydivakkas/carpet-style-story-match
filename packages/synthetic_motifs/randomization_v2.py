"""
Domain Randomization Engine V2 for Synthetic Carpet Motifs.
Implements photorealistic physical, geometric, optical, and morphological realism:
1. Procedural Weave & Knot Texture (Multi-octave noise, directional striation, vignetting)
2. Fiber Abrasion & Distressed Wear Masks (0-25% controlled erosion)
3. Chromatic Aging & Regional Fading (Non-uniform gamma/saturation, vegetal antique palettes)
4. Handmade Elastic Warp & Knot Jitter (Non-rigid elastic displacement + 1-3px jitter + perspective tilt)
5. Camera & Optical Degradation Chain (Lighting gradients, defocus blur, sensor noise, JPEG artifacts)
6. Strict Directional Orientation Policy (Direction-locked motifs: tree, mihrap, humanoid)

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass, field
import math
import numpy as np
import cv2

from packages.synthetic_motifs.geometry import Polygon, BoundingBox, OrientedBoundingBox, create_homography_matrix


# Expanded Antique Natural Dye Palettes
ANTIQUE_NATURAL_PALETTES = [
    # 1. Bergama Madder & Indigo
    {
        "name": "bergama_madder_indigo",
        "background": (224, 218, 202),      # Muted Weathered Cream
        "field": (34, 42, 138),             # Natural Madder Root Red (BGR)
        "border_outer": (118, 64, 28),      # Oxidized Indigo Blue
        "border_inner": (195, 178, 142),    # Aged Sand
        "motifs": [(230, 222, 205), (42, 135, 172), (115, 60, 25), (48, 105, 52), (28, 38, 125)],
    },
    # 2. Ushak Terracotta & Sage
    {
        "name": "ushak_terracotta_sage",
        "background": (212, 205, 188),
        "field": (48, 82, 155),             # Soft Terracotta
        "border_outer": (82, 112, 75),      # Faded Sage Green
        "border_inner": (218, 208, 185),
        "motifs": [(235, 228, 210), (32, 40, 128), (88, 118, 78), (35, 142, 188)],
    },
    # 3. Konya Ochre & Lapis
    {
        "name": "konya_ochre_lapis",
        "background": (218, 212, 198),
        "field": (132, 72, 35),             # Deep Lapis Blue
        "border_outer": (38, 132, 192),     # Raw Yellow Ochre
        "border_inner": (198, 188, 168),
        "motifs": [(228, 220, 202), (32, 128, 185), (45, 55, 152), (58, 122, 65)],
    },
    # 4. Gordes Walnut & Saffron
    {
        "name": "gordes_walnut_saffron",
        "background": (208, 200, 182),
        "field": (45, 55, 78),              # Walnut Husk Brown
        "border_outer": (42, 148, 205),     # Saffron Gold
        "border_inner": (215, 205, 180),
        "motifs": [(232, 224, 208), (40, 52, 140), (75, 115, 82), (35, 138, 195)],
    },
    # 5. Milas Apricot & Tobacco
    {
        "name": "milas_apricot_tobacco",
        "background": (222, 214, 196),
        "field": (62, 118, 182),            # Muted Apricot/Rose
        "border_outer": (45, 68, 92),       # Tobacco Brown
        "border_inner": (205, 195, 172),
        "motifs": [(238, 230, 212), (52, 98, 165), (70, 108, 74), (32, 42, 115)],
    },
    # 6. Ladik Pomegranate & Ivory
    {
        "name": "ladik_pomegranate_ivory",
        "background": (230, 225, 210),
        "field": (28, 32, 125),             # Deep Pomegranate
        "border_outer": (125, 75, 32),      # Sea Blue
        "border_inner": (220, 210, 190),
        "motifs": [(242, 238, 225), (40, 145, 185), (55, 110, 60), (25, 30, 118)],
    },
]


@dataclass
class DomainRandomizationV2Config:
    """Configurable parameter space for Domain Randomization V2."""
    enabled: bool = True
    
    # 1. Texture parameters
    texture_enabled: bool = True
    knot_frequency_range: Tuple[float, float] = (3.0, 7.0)  # pixels per knot
    knot_amplitude_range: Tuple[float, float] = (0.04, 0.12)
    weave_octaves: int = 3
    vignette_intensity_range: Tuple[float, float] = (0.10, 0.35)

    # 2. Wear & Abrasion parameters
    wear_enabled: bool = True
    wear_prob: float = 0.70
    wear_max_fraction: float = 0.25  # Max 25% motif erosion
    wear_fuzziness: float = 0.60

    # 3. Chromatic Aging & Fading parameters
    fading_enabled: bool = True
    gamma_range: Tuple[float, float] = (0.80, 1.25)
    saturation_range: Tuple[float, float] = (0.65, 1.15)
    regional_fade_cells: Tuple[int, int] = (6, 6)

    # 4. Handmade Elastic Warp & Jitter
    warp_enabled: bool = True
    elastic_warp_prob: float = 0.85
    elastic_displacement_max: float = 4.0  # pixels
    knot_jitter_max: float = 2.0           # 1-3 px vertex jitter
    perspective_tilt_deg_max: float = 12.0 # +/- 12 degrees

    # 5. Camera & Optical Chain
    camera_chain_enabled: bool = True
    lighting_gradient_strength: Tuple[float, float] = (0.10, 0.28)
    defocus_blur_prob: float = 0.65
    defocus_sigma_range: Tuple[float, float] = (0.4, 1.3)
    sensor_noise_prob: float = 0.75
    sensor_noise_sigma: Tuple[float, float] = (2.5, 9.0)
    jpeg_quality_range: Tuple[int, int] = (60, 95)

    # 6. Directional Policy
    directional_policy_enabled: bool = True
    direction_locked_angle_max: float = 8.0  # +/- 8 deg for tree, mihrap, humanoid


class ProceduralWeaveTextureEngine:
    """Procedurally synthesizes multi-octave carpet knot ribs and directional striations."""

    @staticmethod
    def generate_weave_texture(
        width: int,
        height: int,
        knot_freq: float = 4.5,
        amplitude: float = 0.08,
        rng: Optional[np.random.RandomState] = None,
    ) -> np.ndarray:
        if rng is None:
            rng = np.random.RandomState(42)

        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # Base directional warp/weft grid
        phase_x = float(rng.uniform(0, 2 * np.pi))
        phase_y = float(rng.uniform(0, 2 * np.pi))
        weft = np.sin(xx * (2.0 * np.pi / knot_freq) + phase_x)
        warp = np.cos(yy * (2.0 * np.pi / knot_freq) + phase_y)

        # Micro fiber noise octave
        noise_grid = rng.normal(0, 0.35, (height // 4 + 1, width // 4 + 1)).astype(np.float32)
        noise_up = cv2.resize(noise_grid, (width, height), interpolation=cv2.INTER_CUBIC)

        combined = 0.55 * (weft * warp) + 0.45 * noise_up
        tex_norm = np.clip(combined * (amplitude * 255.0), -40.0, 40.0)
        return tex_norm[:, :, None].repeat(3, axis=2)

    @staticmethod
    def apply_vignette(
        image: np.ndarray,
        intensity: float = 0.22,
    ) -> np.ndarray:
        h, w = image.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        max_r = math.sqrt(cx * cx + cy * cy)

        x = np.arange(w, dtype=np.float32) - cx
        y = np.arange(h, dtype=np.float32) - cy
        xx, yy = np.meshgrid(x, y)
        r = np.sqrt(xx * xx + yy * yy) / max_r

        vignette_map = 1.0 - intensity * (r ** 2)
        vignette_map = np.clip(vignette_map[:, :, None], 0.0, 1.0)
        return np.clip(image.astype(np.float32) * vignette_map, 0, 255).astype(np.uint8)


class AbrasionWearEngine:
    """Simulates localized knot erosion and fiber wear masks (0-25% controlled)."""

    @staticmethod
    def apply_abrasion(
        image: np.ndarray,
        base_canvas_color: Tuple[int, int, int],
        max_fraction: float = 0.20,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        out = image.astype(np.float32)

        # Multi-scale procedural erosion mask
        low_noise = rng.uniform(0, 1, (h // 24 + 1, w // 24 + 1)).astype(np.float32)
        low_noise = cv2.GaussianBlur(low_noise, (5, 5), 1.5)
        wear_map = cv2.resize(low_noise, (w, h), interpolation=cv2.INTER_CUBIC)

        # Threshold to control abrasion fraction
        thresh = float(rng.uniform(1.0 - max_fraction, 0.98))
        mask = (wear_map > thresh).astype(np.float32)
        mask = cv2.GaussianBlur(mask, (7, 7), 2.0)[:, :, None]

        # Blend eroded zones into antique base canvas tint
        tint_bg = np.array(base_canvas_color, dtype=np.float32)[None, None, :]
        distressed_tint = tint_bg * 0.90 + np.array([30.0, 30.0, 30.0], dtype=np.float32)
        out = out * (1.0 - mask * 0.65) + distressed_tint * (mask * 0.65)

        eroded_area_pct = float(np.mean(mask > 0.1) * 100.0)
        return np.clip(out, 0, 255).astype(np.uint8), {"eroded_area_pct": round(eroded_area_pct, 2)}


class ColorAgingFadingEngine:
    """Applies regional non-uniform chromatic fading and vegetable dye aging."""

    @staticmethod
    def apply_fading(
        image: np.ndarray,
        gamma_range: Tuple[float, float] = (0.85, 1.20),
        sat_range: Tuple[float, float] = (0.70, 1.10),
        grid_size: Tuple[int, int] = (6, 6),
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        gx, gy = grid_size

        # Low-frequency saturation multiplier map
        sat_grid = rng.uniform(sat_range[0], sat_range[1], (gy, gx)).astype(np.float32)
        sat_map = cv2.resize(sat_grid, (w, h), interpolation=cv2.INTER_CUBIC)

        # Low-frequency gamma map
        gamma_grid = rng.uniform(gamma_range[0], gamma_range[1], (gy, gx)).astype(np.float32)
        gamma_map = cv2.resize(gamma_grid, (w, h), interpolation=cv2.INTER_CUBIC)

        # Convert to HSV for saturation scaling
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_map, 0.0, 255.0)
        bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0

        # Apply regional gamma
        bgr = np.clip(np.power(bgr, gamma_map[:, :, None]), 0.0, 1.0)
        out = (bgr * 255.0).astype(np.uint8)

        return out, {
            "mean_sat_mult": float(np.mean(sat_map)),
            "mean_gamma": float(np.mean(gamma_map))
        }


class HandmadeElasticWarpEngine:
    """Applies non-rigid elastic deformation, knot vertex jitter, and 3D perspective tilt."""

    @staticmethod
    def apply_elastic_and_jitter(
        image: np.ndarray,
        polygons: List[Polygon],
        max_displacement: float = 3.5,
        jitter_max: float = 2.0,
        tilt_deg_max: float = 10.0,
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, List[Polygon], Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]

        # 1. Perspective tilt homography
        tilt_x = float(rng.uniform(-tilt_deg_max, tilt_deg_max))
        tilt_y = float(rng.uniform(-tilt_deg_max, tilt_deg_max))
        
        # Subtle 3D rotation matrix
        ang_x = math.radians(tilt_x)
        ang_y = math.radians(tilt_y)
        foc = float(max(w, h)) * 1.5
        
        src_pts = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        # Perspective projection
        dx1 = math.tan(ang_y) * (h * 0.08)
        dy1 = math.tan(ang_x) * (w * 0.08)
        dst_pts = np.array([
            [dx1, dy1],
            [w - dx1, -dy1],
            [w + dx1, h + dy1],
            [-dx1, h - dy1],
        ], dtype=np.float32)

        H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_img = cv2.warpPerspective(image, H, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        # 2. Smooth elastic displacement grid
        grid_step = 32
        gw = w // grid_step + 2
        gh = h // grid_step + 2
        dx_grid = rng.normal(0, max_displacement, (gh, gw)).astype(np.float32)
        dy_grid = rng.normal(0, max_displacement, (gh, gw)).astype(np.float32)
        dx_grid = cv2.GaussianBlur(dx_grid, (5, 5), 1.8)
        dy_grid = cv2.GaussianBlur(dy_grid, (5, 5), 1.8)

        dx_map = cv2.resize(dx_grid, (w, h), interpolation=cv2.INTER_CUBIC)
        dy_map = cv2.resize(dy_grid, (w, h), interpolation=cv2.INTER_CUBIC)

        map_x = (np.arange(w, dtype=np.float32)[None, :].repeat(h, axis=0) + dx_map).astype(np.float32)
        map_y = (np.arange(h, dtype=np.float32)[:, None].repeat(w, axis=1) + dy_map).astype(np.float32)
        elastic_img = cv2.remap(warped_img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        # 3. Transform Polygons with Homography + Elastic displacement + Knot Jitter
        transformed_polys: List[Polygon] = []
        for poly in polygons:
            new_verts: List[Tuple[float, float]] = []
            for vx, vy in poly.vertices:
                # Apply homography
                pt_h = np.array([vx, vy, 1.0], dtype=np.float64)
                dst_h = H @ pt_h
                px = dst_h[0] / (dst_h[2] + 1e-8)
                py = dst_h[1] / (dst_h[2] + 1e-8)

                # Add elastic offset at (px, py)
                ix = int(np.clip(round(px), 0, w - 1))
                iy = int(np.clip(round(py), 0, h - 1))
                px += float(dx_map[iy, ix])
                py += float(dy_map[iy, ix])

                # Knot discrete jitter (1-3px)
                jx = float(rng.uniform(-jitter_max, jitter_max))
                jy = float(rng.uniform(-jitter_max, jitter_max))
                px = float(np.clip(px + jx, 0.0, float(w - 1)))
                py = float(np.clip(py + jy, 0.0, float(h - 1)))
                new_verts.append((px, py))

            transformed_polys.append(Polygon(new_verts))

        provenance = {
            "tilt_x_deg": tilt_x,
            "tilt_y_deg": tilt_y,
            "max_elastic_displacement": max_displacement,
            "jitter_max": jitter_max,
        }
        return elastic_img, transformed_polys, provenance


class CameraOpticalChainEngine:
    """Applies camera sensor noise, defocus blur, lighting gradients, and compression artifacts."""

    @staticmethod
    def apply_chain(
        image: np.ndarray,
        light_strength: float = 0.18,
        defocus_prob: float = 0.65,
        sensor_noise_prob: float = 0.75,
        jpeg_quality_range: Tuple[int, int] = (65, 95),
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if rng is None:
            rng = np.random.RandomState(42)

        h, w = image.shape[:2]
        out = image.copy().astype(np.float32)
        applied = {}

        # 1. 2D Lighting Gradient (Soft angle cast)
        ang = float(rng.uniform(0, 2 * np.pi))
        lx = np.cos(ang)
        ly = np.sin(ang)
        x_norm = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        y_norm = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        xx, yy = np.meshgrid(x_norm, y_norm)
        grad = 1.0 + light_strength * (xx * lx + yy * ly)
        out = np.clip(out * grad[:, :, None], 0, 255)
        applied["lighting_gradient_angle"] = round(math.degrees(ang), 1)

        # 2. Defocus / Gaussian Blur
        if rng.uniform(0, 1) < defocus_prob:
            sigma = float(rng.uniform(0.4, 1.2))
            out = cv2.GaussianBlur(out, (0, 0), sigma)
            applied["defocus_sigma"] = round(sigma, 2)

        # 3. Sensor Noise (Poisson-Gaussian)
        if rng.uniform(0, 1) < sensor_noise_prob:
            std = float(rng.uniform(2.5, 8.0))
            noise = rng.normal(0, std, out.shape).astype(np.float32)
            out = np.clip(out + noise, 0, 255)
            applied["sensor_noise_std"] = round(std, 2)

        # 4. JPEG Compression
        out_uint8 = np.clip(out, 0, 255).astype(np.uint8)
        jq = int(rng.randint(jpeg_quality_range[0], jpeg_quality_range[1] + 1))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jq]
        _, encimg = cv2.imencode(".jpg", out_uint8, encode_param)
        final_img = cv2.imdecode(encimg, 1)
        applied["jpeg_quality"] = jq

        return final_img, applied


class DirectionalPolicyEngine:
    """Enforces culturally authentic rotation and symmetry constraints."""

    # Motifs strictly locked to upright vertical axis (+/- 8 deg)
    DIRECTION_LOCKED_KEYS = {
        "tree_like",
        "niche_like",
        "human_figure_like_geometric",
    }

    @classmethod
    def sample_rotation(
        cls,
        motif_key: str,
        rng: np.random.RandomState,
        max_locked_angle: float = 8.0,
    ) -> float:
        if motif_key in cls.DIRECTION_LOCKED_KEYS:
            # Tree, Mihrap, Elibelinde MUST remain upright; upside-down mihrap is forbidden.
            return float(rng.uniform(-max_locked_angle, max_locked_angle))
        elif motif_key in {"medallion_like", "octagonal_form", "star_like", "rosette_like"}:
            # Radial / polygonal symmetry
            return float(rng.uniform(-45.0, 45.0))
        else:
            # General decorative forms (palmette, horn, hook, lotus, comb)
            return float(rng.uniform(-180.0, 180.0))
