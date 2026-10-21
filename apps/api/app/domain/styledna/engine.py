import io
import math
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import cv2
from PIL import Image

from app.db.models.carpet_style_profile import StyleProfileStatus, StyleDimensionStatus
from app.domain.styledna.exceptions import StyleDNAAnalysisFailedError

STYLE_DNA_ALGORITHM_VERSION = "style-dna-v1.0.0"
ANALYSIS_MAX_SIDE = 1024

class StyleDNAImageContext:
    """Pre-processes and caches image color spaces and feature maps for Style DNA calculations."""

    def __init__(self, raw_bytes: bytes):
        # Decode image using OpenCV
        nparr = np.frombuffer(raw_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            # Fallback to Pillow
            try:
                pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise StyleDNAAnalysisFailedError(f"Could not decode image for analysis: {e}") from e

        h, w = img_bgr.shape[:2]
        if max(h, w) > ANALYSIS_MAX_SIDE:
            scale = ANALYSIS_MAX_SIDE / float(max(h, w))
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
            img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=interp)

        self.bgr = img_bgr
        self.height, self.width = self.bgr.shape[:2]
        self.rgb = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2RGB)
        self.gray = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2GRAY)
        self.hsv = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2HSV)
        self.lab = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2Lab)

        # Pre-calculate Canny edges and Sobel gradients
        self.edges = cv2.Canny(self.gray, 50, 150)
        grad_x = cv2.Sobel(self.gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(self.gray, cv2.CV_64F, 0, 1, ksize=3)
        self.grad_mag = np.sqrt(grad_x**2 + grad_y**2)

class StyleDNAEngine:
    """Deterministic, model-free computer vision engine for 9D Style DNA extraction."""

    def analyze(self, raw_bytes: bytes) -> Tuple[StyleProfileStatus, List[Dict[str, Any]]]:
        ctx = StyleDNAImageContext(raw_bytes)
        dimensions = []

        dim_extractors = [
            ("color_energy", self._calc_d1_color_energy),
            ("color_diversity", self._calc_d2_color_diversity),
            ("contrast", self._calc_d3_contrast),
            ("warmth", self._calc_d4_warmth),
            ("visual_complexity", self._calc_d5_visual_complexity),
            ("structural_order", self._calc_d6_structural_order),
            ("rhythm_repetition", self._calc_d7_rhythm_repetition),
            ("focal_strength", self._calc_d8_focal_strength),
            ("form_language", self._calc_d9_form_language),
        ]

        has_available = False
        has_failed_or_missing = False

        for key, fn in dim_extractors:
            try:
                res = fn(ctx)
                dimensions.append(res)
                if res["status"] in [StyleDimensionStatus.AVAILABLE, StyleDimensionStatus.LOW_CONFIDENCE]:
                    has_available = True
                if res["status"] in [StyleDimensionStatus.NOT_AVAILABLE, StyleDimensionStatus.FAILED]:
                    has_failed_or_missing = True
            except Exception as e:
                has_failed_or_missing = True
                dimensions.append({
                    "key": key,
                    "value": None,
                    "confidence": 0.0,
                    "status": StyleDimensionStatus.FAILED,
                    "evidence": {"error": str(e)},
                    "method_version": "v1"
                })

        if not has_available:
            profile_status = StyleProfileStatus.FAILED
        elif has_failed_or_missing:
            profile_status = StyleProfileStatus.PARTIAL
        else:
            profile_status = StyleProfileStatus.COMPLETE

        return profile_status, dimensions

    def _calc_d1_color_energy(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Lab Chroma
        l, a, b = cv2.split(ctx.lab.astype(np.float32))
        a_star = a - 128.0
        b_star = b - 128.0
        chroma = np.sqrt(a_star**2 + b_star**2)
        chroma_mean = float(np.mean(chroma))
        chroma_p75 = float(np.percentile(chroma, 75))

        # Hasler-Süsstrunk Colorfulness
        r, g, b_c = cv2.split(ctx.rgb.astype(np.float32))
        rg = np.abs(r - g)
        yb = np.abs(0.5 * (r + g) - b_c)
        std_rg = float(np.std(rg))
        mean_rg = float(np.mean(rg))
        std_yb = float(np.std(yb))
        mean_yb = float(np.mean(yb))
        std_rgyb = math.sqrt(std_rg**2 + std_yb**2)
        mean_rgyb = math.sqrt(mean_rg**2 + mean_yb**2)
        colorfulness = std_rgyb + 0.3 * mean_rgyb

        # Scaled value
        v_chroma = min(1.0, chroma_mean / 60.0)
        v_colorful = min(1.0, colorfulness / 80.0)
        value = float(np.clip(0.5 * v_chroma + 0.5 * v_colorful, 0.0, 1.0))
        confidence = float(np.clip(min(1.0, chroma_p75 / 30.0), 0.3, 1.0))

        return {
            "key": "color_energy",
            "value": round(value, 4),
            "confidence": round(confidence, 4),
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "chroma_mean": round(chroma_mean, 2),
                "chroma_p75": round(chroma_p75, 2),
                "colorfulness": round(colorfulness, 2)
            },
            "method_version": "d1-v1"
        }

    def _calc_d2_color_diversity(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Lab color quantization into 8x8x8 bins
        lab_flat = ctx.lab.reshape(-1, 3)
        bins = (lab_flat // 32).astype(np.int32)
        bin_indices = bins[:, 0] * 64 + bins[:, 1] * 8 + bins[:, 2]

        counts = np.bincount(bin_indices, minlength=512)
        total_pixels = len(bin_indices)
        probs = counts / float(total_pixels)

        # Ignore insignificant noise bins (< 0.1% population)
        sig_probs = probs[probs >= 0.001]
        active_bins = len(sig_probs)

        if active_bins == 0:
            entropy = 0.0
            effective_colors = 1.0
        else:
            entropy = float(-np.sum(sig_probs * np.log(sig_probs)))
            effective_colors = float(np.exp(entropy))

        # Max entropy for 64 significant bins is ln(64) ≈ 4.15
        value = float(np.clip(entropy / 4.15, 0.0, 1.0))
        confidence = 1.0 if total_pixels >= 1000 else 0.7

        return {
            "key": "color_diversity",
            "value": round(value, 4),
            "confidence": round(confidence, 4),
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "entropy": round(entropy, 4),
                "effective_colors": round(effective_colors, 2),
                "active_bins": active_bins
            },
            "method_version": "d2-v1"
        }

    def _calc_d3_contrast(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        p05 = float(np.percentile(ctx.gray, 5))
        p95 = float(np.percentile(ctx.gray, 95))
        lum_range = p95 - p05

        # Local tile RMS std
        h, w = ctx.gray.shape
        tile_h, tile_w = max(8, h // 8), max(8, w // 8)
        stds = []
        for r in range(0, h - tile_h + 1, tile_h):
            for c in range(0, w - tile_w + 1, tile_w):
                tile = ctx.gray[r:r+tile_h, c:c+tile_w]
                stds.append(float(np.std(tile)))
        mean_tile_std = float(np.mean(stds)) if stds else float(np.std(ctx.gray))

        v_range = min(1.0, lum_range / 220.0)
        v_std = min(1.0, mean_tile_std / 70.0)
        value = float(np.clip(0.6 * v_range + 0.4 * v_std, 0.0, 1.0))

        return {
            "key": "contrast",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "lum_p05": round(p05, 1),
                "lum_p95": round(p95, 1),
                "lum_range": round(lum_range, 1),
                "tile_rms_std": round(mean_tile_std, 2)
            },
            "method_version": "d3-v1"
        }

    def _calc_d4_warmth(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        h_channel = ctx.hsv[:, :, 0].astype(np.float32)  # 0..180
        s_channel = ctx.hsv[:, :, 1].astype(np.float32) / 255.0  # 0..1

        # Saturation weighting
        mean_sat = float(np.mean(s_channel))

        # Hue warmth mapping:
        # Red/Orange/Yellow: H in [0..30] U [150..180] -> warm (1.0)
        # Cyan/Blue: H in [85..135] -> cool (0.0)
        # Green / Magenta transitions
        warm_weights = np.zeros_like(h_channel)
        
        # Warm zones
        m_warm1 = (h_channel <= 30)
        m_warm2 = (h_channel >= 150)
        warm_weights[m_warm1] = 1.0 - (h_channel[m_warm1] / 60.0)  # 1.0 down to 0.5
        warm_weights[m_warm2] = 0.5 + ((h_channel[m_warm2] - 150.0) / 60.0)  # 0.5 up to 1.0

        # Cool zones
        m_cool = (h_channel >= 85) & (h_channel <= 135)
        warm_weights[m_cool] = 0.0

        # Green transition (30..85)
        m_green = (h_channel > 30) & (h_channel < 85)
        warm_weights[m_green] = 0.5 * (1.0 - (h_channel[m_green] - 30.0) / 55.0)

        # Magenta transition (135..150)
        m_mag = (h_channel > 135) & (h_channel < 150)
        warm_weights[m_mag] = 0.5 * ((h_channel[m_mag] - 135.0) / 15.0)

        # Chromatic weighted sum
        total_chroma = np.sum(s_channel)
        if total_chroma < 1.0 or mean_sat < 0.05:
            # Low chromatic evidence -> neutral warmth 0.5 with LOW_CONFIDENCE
            return {
                "key": "warmth",
                "value": 0.5,
                "confidence": 0.3,
                "status": StyleDimensionStatus.LOW_CONFIDENCE,
                "evidence": {
                    "mean_saturation": round(mean_sat, 4),
                    "note": "Low chromatic evidence, neutral default"
                },
                "method_version": "d4-v1"
            }

        warmth_score = float(np.sum(warm_weights * s_channel) / total_chroma)
        value = float(np.clip(warmth_score, 0.0, 1.0))
        confidence = float(np.clip(mean_sat * 3.0, 0.5, 1.0))

        return {
            "key": "warmth",
            "value": round(value, 4),
            "confidence": round(confidence, 4),
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "mean_saturation": round(mean_sat, 4),
                "warmth_score": round(warmth_score, 4)
            },
            "method_version": "d4-v1"
        }

    def _calc_d5_visual_complexity(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Edge density
        edge_density = float(np.mean(ctx.edges > 0))

        # FFT High Frequency Energy Ratio
        f = np.fft.fft2(ctx.gray.astype(np.float32))
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.abs(fshift)
        
        h, w = ctx.gray.shape
        cy, cx = h // 2, w // 2
        r = min(cy, cx) // 4
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)
        
        high_freq_mask = dist_from_center > r
        high_freq_energy = float(np.sum(magnitude_spectrum[high_freq_mask]))
        total_energy = float(np.sum(magnitude_spectrum) + 1e-6)
        fft_ratio = high_freq_energy / total_energy

        # Laplacian contour variance
        laplacian_var = float(cv2.Laplacian(ctx.gray, cv2.CV_64F).var())
        v_lap = min(1.0, math.log1p(laplacian_var) / 8.0)

        v_edge = min(1.0, edge_density / 0.15)
        value = float(np.clip(0.4 * v_edge + 0.3 * fft_ratio + 0.3 * v_lap, 0.0, 1.0))

        return {
            "key": "visual_complexity",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "edge_density": round(edge_density, 4),
                "fft_high_freq_ratio": round(fft_ratio, 4),
                "laplacian_var": round(laplacian_var, 2)
            },
            "method_version": "d5-v1"
        }

    def _calc_d6_structural_order(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Vertical Reflection Similarity
        gray_f = ctx.gray.astype(np.float32)
        flipped_v = cv2.flip(gray_f, 1)  # Horizontal flip -> Vertical axis symmetry
        mse_v = float(np.mean((gray_f - flipped_v)**2))
        sym_v = float(np.clip(1.0 - (mse_v / 4000.0), 0.0, 1.0))

        # Horizontal Reflection Similarity
        flipped_h = cv2.flip(gray_f, 0)  # Vertical flip -> Horizontal axis symmetry
        mse_h = float(np.mean((gray_f - flipped_h)**2))
        sym_h = float(np.clip(1.0 - (mse_h / 4000.0), 0.0, 1.0))

        # Spatial Centroid Balance
        M = cv2.moments(ctx.gray)
        if M["m00"] != 0:
            cX = M["m10"] / M["m00"]
            cY = M["m01"] / M["m00"]
            offset_x = abs(cX - ctx.width / 2.0) / (ctx.width / 2.0)
            offset_y = abs(cY - ctx.height / 2.0) / (ctx.height / 2.0)
            balance = float(np.clip(1.0 - 0.5 * (offset_x + offset_y), 0.0, 1.0))
        else:
            balance = 0.5

        value = float(np.clip(0.4 * sym_v + 0.3 * sym_h + 0.3 * balance, 0.0, 1.0))

        return {
            "key": "structural_order",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "vertical_symmetry": round(sym_v, 4),
                "horizontal_symmetry": round(sym_h, 4),
                "centroid_balance": round(balance, 4)
            },
            "method_version": "d6-v1"
        }

    def _calc_d7_rhythm_repetition(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # 2D Autocorrelation via 2D FFT
        gray_f = ctx.gray.astype(np.float32)
        gray_norm = gray_f - np.mean(gray_f)
        
        f = np.fft.fft2(gray_norm)
        power = np.abs(f)**2
        autocorr = np.real(np.fft.ifft2(power))
        
        # Shift zero-frequency component to center
        autocorr_shift = np.fft.fftshift(autocorr)
        max_val = float(autocorr_shift.max()) + 1e-6
        autocorr_norm = autocorr_shift / max_val

        # Zero out central peak region (radius 20px)
        h, w = autocorr_norm.shape
        cy, cx = h // 2, w // 2
        y_grid, x_grid = np.ogrid[:h, :w]
        dist = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)
        autocorr_norm[dist <= 20] = 0.0

        # Off-center peaks detection
        threshold = 0.25
        peaks = autocorr_norm[autocorr_norm > threshold]
        peak_count = int(len(peaks))
        max_peak = float(peaks.max()) if peak_count > 0 else 0.0

        v_peak = min(1.0, max_peak / 0.7)
        v_count = min(1.0, math.log1p(peak_count) / 6.0)
        value = float(np.clip(0.6 * v_peak + 0.4 * v_count, 0.0, 1.0))

        return {
            "key": "rhythm_repetition",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "off_center_peak_count": peak_count,
                "max_peak_strength": round(max_peak, 4)
            },
            "method_version": "d7-v1"
        }

    def _calc_d8_focal_strength(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Spatial Visual Energy Map (Gradient + Local Contrast)
        energy_map = ctx.grad_mag.copy()

        h, w = energy_map.shape
        grid_h, grid_w = 8, 8
        tile_h, tile_w = h // grid_h, w // grid_w

        tile_energies = []
        for r in range(grid_h):
            for c in range(grid_w):
                t = energy_map[r*tile_h:(r+1)*tile_h, c*tile_w:(c+1)*tile_w]
                tile_energies.append(float(np.sum(t)))

        tile_energies = np.array(tile_energies)
        total_energy = float(tile_energies.sum()) + 1e-6
        probs = tile_energies / total_energy

        # Uniform distribution entropy = ln(64) ≈ 4.1588
        max_entropy = math.log(64)
        entropy = float(-np.sum(probs[probs > 0] * np.log(probs[probs > 0])))
        entropy_deficit = float(np.clip((max_entropy - entropy) / max_entropy, 0.0, 1.0))

        # Top 10% (top 6 tiles) energy concentration ratio
        sorted_probs = np.sort(probs)[::-1]
        top10_ratio = float(np.sum(sorted_probs[:6]))

        value = float(np.clip(0.6 * entropy_deficit + 0.4 * min(1.0, top10_ratio / 0.5), 0.0, 1.0))

        return {
            "key": "focal_strength",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "entropy_deficit": round(entropy_deficit, 4),
                "top10_energy_ratio": round(top10_ratio, 4)
            },
            "method_version": "d8-v1"
        }

    def _calc_d9_form_language(self, ctx: StyleDNAImageContext) -> Dict[str, Any]:
        # Insufficient Edge Evidence Check
        total_edge_pixels = int(np.sum(ctx.edges > 0))
        if total_edge_pixels < 100:
            return {
                "key": "form_language",
                "value": None,
                "confidence": 0.0,
                "status": StyleDimensionStatus.NOT_AVAILABLE,
                "evidence": {
                    "total_edge_pixels": total_edge_pixels,
                    "reason": "Insufficient edge content for shape analysis"
                },
                "method_version": "d9-v1"
            }

        # Hough Straight Line Support
        lines = cv2.HoughLinesP(ctx.edges, 1, np.pi / 180, threshold=40, minLineLength=25, maxLineGap=5)
        straight_line_pixels = 0
        if lines is not None:
            line_mask = np.zeros_like(ctx.edges)
            for line in lines:
                # OpenCV sürümleri (N,1,4) veya (N,4) döndürebilir.
                x1, y1, x2, y2 = [int(v) for v in np.asarray(line).reshape(-1)[:4]]
                cv2.line(line_mask, (x1, y1), (x2, y2), 255, 2)
            straight_line_pixels = int(np.sum((line_mask > 0) & (ctx.edges > 0)))

        straight_ratio = float(np.clip(straight_line_pixels / float(total_edge_pixels + 1e-6), 0.0, 1.0))

        # Contour Curvature / Organic Evidence
        contour_output = cv2.findContours(ctx.edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        contours = contour_output[-2]  # OpenCV iki/üç elemanlı dönüş uyumluluğu
        organic_score_acc = 0.0
        contour_count = 0

        for cnt in contours:
            if len(cnt) > 20:
                contour_count += 1
                poly = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
                # Curved contours have more points relative to bounding box perimeter
                ratio = len(cnt) / float(len(poly) + 1e-6)
                organic_score_acc += min(1.0, ratio / 5.0)

        organic_avg = (organic_score_acc / contour_count) if contour_count > 0 else 0.5
        
        # Bipolar: 0.0 = Geometric, 1.0 = Organic
        # Organic value = 1.0 - straight_ratio
        raw_organic = 0.6 * (1.0 - straight_ratio) + 0.4 * organic_avg
        value = float(np.clip(raw_organic, 0.0, 1.0))

        return {
            "key": "form_language",
            "value": round(value, 4),
            "confidence": 1.0,
            "status": StyleDimensionStatus.AVAILABLE,
            "evidence": {
                "straight_line_ratio": round(straight_ratio, 4),
                "organic_contour_ratio": round(organic_avg, 4)
            },
            "method_version": "d9-v1"
        }
