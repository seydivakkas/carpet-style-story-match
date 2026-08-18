# V2-09A — Procedural Motif Dataset Foundation Documentation

## 1. Executive Summary

`packages/synthetic_motifs/` establishes an offline, deterministic procedural synthetic dataset foundation for carpet visual motif detection and evaluation. It generates vector geometries for all 17 frozen `VisualCandidateKey` ontology classes, projects exact ground truth (axis-aligned bounding boxes, polygonal contours, minimum-area oriented bounding boxes, and pixel-accurate raster masks) through domain randomization transforms, and exports to canonical JSON, COCO 1.0, YOLO Detect, YOLO OBB (Ultralytics standard), and YOLO Segment formats.

```
MotifPrimitiveRegistry (17 VisualCandidateKey classes)
        ↓
Parameterized Motif Vector Primitives
        ↓
CarpetComposer (Borders, Medallions, Niches, Grids, Lattices)
        ↓
Clean Geometry Scene Graph (Instance IDs, Canonical Polygons)
        ↓
Domain Randomization (Perspective Homography, Affine, Textures, Occlusion)
        ↓
Transformed Ground Truth (BBox, Polygon, OBB, Mask, Provenance)
        ↓
Multi-Format Dataset Exporters (JSON, COCO, YOLO Detect, YOLO OBB, YOLO Segment)
```

---

## 2. Core Governance Invariants & Limitations

> [!IMPORTANT]
> **Strict Frozen Principles**:
> - **Visual Labels Only**: Labels are strictly visual candidate keys (`star_like`, `niche_like`, `tree_like`, etc.). Zero cultural claims, symbolism, dynasty, historical period, or personality inferences are permitted in dataset annotations.
> - **Synthetic GT != Real-World Accuracy**: High Average Precision (AP) on synthetic test sets does not imply equivalent performance on historical or catalog carpets.
> - **Synthetic Motif != Cultural Evidence**: Procedural shapes represent synthetic visual geometry ground truth for object detection benchmarks; they do not establish historical authenticity.
> - **Zero Database Mutations**: The dataset generator operates 100% offline and makes zero writes to the production SQLite database `carpet_db.sqlite` (migration head remains `2026_08_17_017`).
> - **Real-World Holdout Benchmark Required**: Subsequent detector benchmarks (V2-09B) cannot be accepted solely on synthetic evaluation; manually annotated real holdout carpet imagery is strictly required.

---

## 3. Visual Candidate Support Matrix

All 17 visual candidate keys from `upload-analysis-v1.0.0` / `motif-ontology-v1.0.0` are procedurally supported:

| # | Visual Candidate Key | Geometry Family | Primitive Class | Scale Bounds | Capabilities |
|---|---|---|---|---|---|
| 0 | `cloud_band_like` | `organic_ribbon` | `CloudBandPrimitive` | `[0.12, 0.65]` | Rotation, Repetition, Polygon, OBB |
| 1 | `comb_like` | `geometric_linear` | `CombPrimitive` | `[0.06, 0.40]` | Rotation, Repetition, Polygon, OBB |
| 2 | `hook_like` | `geometric_polyline` | `HookPrimitive` | `[0.05, 0.40]` | Rotation, Repetition, Polygon, OBB |
| 3 | `horn_like` | `geometric_curvilinear` | `HornPrimitive` | `[0.08, 0.50]` | Rotation, Repetition, Polygon, OBB |
| 4 | `human_figure_like_geometric` | `geometric_stylized_figurative` | `HumanFigurePrimitive` | `[0.10, 0.55]` | Rotation, Repetition, Polygon, OBB |
| 5 | `lattice_like` | `composition_grid` | `LatticePrimitive` | `[0.20, 0.90]` | Rotation, Repetition, Polygon, OBB |
| 6 | `lotus_like` | `organic_cup` | `LotusPrimitive` | `[0.08, 0.50]` | Rotation, Repetition, Polygon, OBB |
| 7 | `lozenge_like` | `geometric_polygon` | `LozengePrimitive` | `[0.08, 0.60]` | Rotation, Repetition, Polygon, OBB |
| 8 | `medallion_like` | `composition_radial` | `MedallionPrimitive` | `[0.15, 0.85]` | Rotation, Repetition, Polygon, OBB |
| 9 | `niche_like` | `architectural_arch` | `NichePrimitive` | `[0.25, 0.90]` | Fixed Vertical, Repetition, Polygon, OBB |
| 10 | `octagonal_form` | `geometric_polygon` | `OctagonPrimitive` | `[0.10, 0.70]` | Rotation, Repetition, Polygon, OBB |
| 11 | `palmette_like` | `organic_fan` | `PalmettePrimitive` | `[0.10, 0.60]` | Rotation, Repetition, Polygon, OBB |
| 12 | `rosette_like` | `organic_radial` | `RosettePrimitive` | `[0.08, 0.50]` | Rotation, Repetition, Polygon, OBB |
| 13 | `star_like` | `geometric_radial` | `StarPrimitive` | `[0.08, 0.60]` | Rotation, Repetition, Polygon, OBB |
| 14 | `tree_like` | `organic_branching` | `TreePrimitive` | `[0.15, 0.80]` | Rotation, Repetition, Polygon, OBB |
| 15 | `unmapped_visual_motif` | `abstract_glyph` | `UnmappedMotifPrimitive` | `[0.06, 0.45]` | Rotation, Repetition, Polygon, OBB |
| 16 | `vine_scroll_like` | `organic_scroll` | `VineScrollPrimitive` | `[0.10, 0.70]` | Rotation, Repetition, Polygon, OBB |

---

## 4. Geometric Oracle & Mathematical Ground Truth

1. **Exact Vector Polygons**: Vertices are maintained in canonical continuous coordinates $(x_i, y_i) \in [0, W] \times [0, H]$.
2. **Homography Projective Propagation**:
   $$\begin{bmatrix} x' \\ y' \\ w' \end{bmatrix} = \mathbf{H} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}, \quad (x_{warp}, y_{warp}) = \left(\frac{x'}{w'}, \frac{y'}{w'}\right)$$
3. **Canvas Boundary Clipping**: Sutherland-Hodgman convex polygon clipping against $[0, W] \times [0, H]$.
4. **Visibility & Truncation**:
   $$\text{visible\_fraction} = \frac{\text{Area}(\text{Polygon}_{\text{clipped}})}{\text{Area}(\text{Polygon}_{\text{original}})}$$
   - $\text{visible\_fraction} < 0.95 \implies \text{is\_truncated} = \text{true}$
   - $\text{visible\_fraction} < 0.20 \implies \text{ignore} = \text{true}$ (retained in JSON, omitted from detection loss)
5. **Oriented Bounding Box (OBB)**: Computed via OpenCV `cv2.minAreaRect` on the transformed, clipped polygon vertices.
6. **Photometric Invariance**: Brightness, contrast, gamma, saturation, and noise augmentations modify pixel values only and leave all geometric annotations identical.

---

## 5. Domain Randomization Layers

- **Geometric**: Perspective homography ($\pm 12\%$ distortion), 2D affine rotation ($\pm 15^\circ$), scale jitter ($[0.85, 1.15]$), translation ($\pm 8\%$).
- **Photometric**: Brightness ($[0.8, 1.2]$), contrast ($[0.8, 1.2]$), gamma ($[0.85, 1.2]$), HSV saturation ($[0.7, 1.3]$).
- **Imaging**: Gaussian blur ($\sigma \in [0.5, 1.5]$), Gaussian noise ($\sigma \in [4, 14]$), JPEG compression ($Q \in [45, 95]$).
- **Material-like**: Procedural yarn weave grid frequency simulation, low-frequency fading wear masks.
- **Occlusion**: Neutral geometric occluders with overlap mask tracking.

---

## 6. Dataset Splits & Leakage Control

- **Splits**: Deterministic 70% `train`, 15% `validation`, 15% `test` based on master seed.
- **Scene Signature**: Computed via SHA-256 hash of compositional layout type, border parameters, and pre-randomization instance geometries.
- **Leakage Prevention**: Cross-split collisions trigger deterministic seed-bumping to guarantee completely disjoint scene signatures between splits.

---

## 7. Multi-Format Exporters

1. **Canonical JSON**: `samples/{sample_id}.json` (Pydantic `SyntheticCarpetSample` format with complete instance geometries and transform provenance).
2. **COCO 1.0**: `annotations/coco_{split}.json` (categories, images, annotations with `bbox` $[x, y, w, h]$, `segmentation`, and custom `obb` fields).
3. **YOLO Detect**: `yolo/labels/{split}/{sample_id}.txt` (`<class_id> <x_center> <y_center> <width> <height>`).
4. **YOLO OBB**: `yolo_obb/labels/{split}/{sample_id}.txt` (`<class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>` in normalized coordinates).
5. **YOLO Segment**: `yolo_segment/labels/{split}/{sample_id}.txt` (`<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>`).

---

## 8. Licensing Audit & Future Model Gates

- **Ultralytics YOLO**: AGPL-3.0 copyleft license. Use for internal non-commercial research/benchmarking only; flag `LICENSE_REVIEW_REQUIRED` before any commercial deployment.
- **Candidate VLM Metadata (Zero Downloads in V2-09A)**:
  - Reference: `Qwen/Qwen2.5-VL-3B-Instruct-AWQ`
  - Small VLM Candidates: `Qwen2-VL-2B-Instruct`, `Qwen3-VL-2B-Instruct`, `SmolVLM2-2.2B-Instruct`, `SmolVLM2-500M-Instruct`, `SmolVLM2-256M-Instruct`, `google/paligemma2-3b-pt-448`.
  - **PaliGemma Gate**: `MANUAL_LICENSE_GATE` (gated license agreement on Hugging Face required).
  - **Qwen/Smol Download Gate**: Explicit `MODEL_DOWNLOAD_APPROVED` required before downloading in future V2-09C.

---

## 9. Controlled Hard-Negative Dataset Contract

Controlled hard negatives are non-target background visual structures engineered to resemble target classes geometrically without receiving positive target detection annotations.

### 9.1 Hard Negative Families
1. `radial_polygon_nonstar` (near `star_like`): Asymmetric 7-point polygon breaking radial star symmetry.
2. `radial_ornament_nonrosette` (near `rosette_like`): Scalloped circular spiky ring without rosette petal geometry.
3. `isolated_lozenge_pattern` (near `lattice_like`): Single standing lozenge element lacking repeating lattice matrix.
4. `octagonal_radial_variant` (near `octagonal_form`, `star_like`): Stepped irregular 8-point polygon.
5. `generic_branching_form` (near `tree_like`): Simple Y-fork stroke lacking tree trunk or foliage structure.

### 9.2 Export & Leakage Semantics
- **Background Only**: Rendered onto image pixels; strictly excluded from positive `instances[]` in COCO, YOLO Detect, YOLO OBB, and YOLO Segment labels.
- **Canonical Provenance**: Recorded in `hard_negatives[]` array in canonical sample JSON.
- **Leakage Threshold**: `positive_label_leak_count = 0` strictly enforced during dataset validation.
- **Scene Signature**: Hard negative geometries participate in `scene_signature` hash computation to prevent cross-split leakage.

---

## 10. Future V2-09 Roadmap

- **V2-09A**: Procedural Dataset Foundation (COMPLETE).
- **V2-09B**: Detector Baseline (YOLO Detection / OBB evaluation on synthetic + real holdout set).
- **V2-09C**: Small-VLM Visual Verifier Benchmark.
- **V2-09D**: Optional QLoRA / Specialist Fine-Tuning.
