# 9D Carpet Style DNA Engine v1 Specification

## 1. Overview & Versioning

- **Algorithm Version**: `style-dna-v1.0.0`
- **Analysis Scope**: `FULL_IMAGE`
- **Analysis Max Side**: `1024` px (aspect ratio preserved, no upscale)
- **Input Hash**: `analysis_input_sha256` (SHA-256 hash of analyzed image bytes)

> **CRITICAL TRUTHFULNESS RULE**:
> Insufficient visual evidence never produces default fallback scores (e.g. 0.50 or fake 0.80 confidence). When evidence is missing or below measurable threshold, `value = None` and `status = NOT_AVAILABLE`.

---

## 2. Dimension Extraction Algorithms

### D1 `color_energy` (Sakin ↔ Canlı)
- **Method**: Lab Chroma Magnitude + Hasler-Süsstrunk Colorfulness + HSV Saturation.
- **Formula**: $\text{chroma} = \sqrt{a^{*2} + b^{*2}}$, colorfulness metric $M = \sigma_{rgyb} + 0.3 \cdot \mu_{rgyb}$.
- **Evidence**: `{"chroma_mean": float, "colorfulness": float, "saturation_p75": float}`.

### D2 `color_diversity` (Sınırlı Palet ↔ Zengin Palet)
- **Method**: Quantized Lab Color Space Entropy + Effective Color Count.
- **Formula**: Insignificant bins (< 0.1% population) pruned. Shannon entropy $H = -\sum p_i \ln p_i$, effective color count $N_{eff} = \exp(H)$.
- **Evidence**: `{"entropy": float, "effective_colors": float, "active_bins": int}`.

### D3 `contrast` (Yumuşak ↔ Güçlü)
- **Method**: Luminance Range ($p_{95} - p_{05}$) + Local Tile RMS Standard Deviation + Edge Contrast.
- **Evidence**: `{"luminance_range": float, "tile_rms_std": float, "edge_contrast": float}`.

### D4 `warmth` (Soğuk ↔ Sıcak)
- **Method**: Bipolar Chromatic Warmth Axis ($0.0 = \text{cool}$, $0.5 = \text{neutral}$, $1.0 = \text{warm}$).
- **Formula**: Circular HSV hue distance weighted by saturation/chroma. Neutral/gray pixels yield value $\approx 0.5$ with `LOW_CONFIDENCE`.
- **Evidence**: `{"warm_ratio": float, "cool_ratio": float, "chroma_weight": float}`.

### D5 `visual_complexity` (Sade ↔ Detaylı)
- **Method**: Multi-Scale Canny Edge Density + High-Frequency FFT Spectral Energy + Laplacian Contour Variance.
- **Invariant**: Strictly decoupled from repetition ($D5 \neq D7$).
- **Evidence**: `{"edge_density": float, "fft_high_freq_ratio": float, "laplacian_var": float}`.

### D6 `structural_order` (Düzen & Simetri)
- **Method**: Bilateral Vertical Reflection Similarity + Horizontal Reflection Similarity + Spatial Centroid Balance.
- **Invariant**: Structural order is strictly decoupled from repetition ($D6 \neq D7$).
- **Evidence**: `{"vertical_symmetry": float, "horizontal_symmetry": float, "centroid_offset": float}`.

### D7 `rhythm_repetition` (Tekil ↔ Ritmik / Tekrarlı)
- **Method**: 2D Autocorrelation via 2D FFT.
- **Pipeline**: Grayscale mean removal $\to$ 2D FFT $\to$ Power Spectrum $\to$ Inverse 2D FFT $\to$ Autocorrelation Map $\to$ center peak removal $\to$ off-center peak detection.
- **Evidence**: `{"peak_count": int, "max_peak_strength": float, "spatial_regularity": float}`.

### D8 `focal_strength` (Dağıtılmış ↔ Güçlü Odak)
- **Method**: Model-free Spatial Visual Energy Concentration (gradient + local contrast) Deficit Entropy.
- **Invariant**: Evaluates concentration anywhere in image ($D8 \neq \text{centrality}$).
- **Evidence**: `{"energy_entropy_deficit": float, "top10_spatial_ratio": float}`.

### D9 `form_language` (Geometrik ↔ Organik)
- **Method**: Bipolar Shape Axis ($0.0 = \text{geometric}$, $0.5 = \text{mixed}$, $1.0 = \text{organic}$).
- **Formula**: Straight-line Hough support vs contour curvature ratio.
- **Evidence**: `{"straight_edge_ratio": float, "contour_curvature": float}`.
- **Status**: If contour evidence is below threshold, `value = None` and `status = NOT_AVAILABLE`.

---

## 3. Database Persistence & Idempotency

- `CarpetStyleProfileModel`: Stores overall analysis status (`COMPLETE`, `PARTIAL`, `FAILED`), algorithm version (`style-dna-v1.0.0`), input hash, and timestamp. Unique constraint `(image_id, algorithm_version)` ensures analysis idempotency.
- `CarpetStyleDimensionModel`: Stores exact 9 dimension records per profile with value, confidence, status, and evidence JSON.

---

## 4. Known Limitations

1. **Full Image Analysis**: Analyzes the complete image without automatic carpet background segmentation.
2. **Model-Free Form Language**: D9 evaluates geometric straightness vs curvilinear curvature, not floral motif object recognition.
3. **Model-Free Focus**: D8 evaluates visual energy concentration, not human eye-tracking saliency.
