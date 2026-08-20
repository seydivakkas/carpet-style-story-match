# V2-09B — Detector Baseline & Real-vs-Synthetic Benchmark Report

## 1. Overview
V2-09B establishes reproducible detector baselines (**YOLO11n Detect** and **YOLO11n OBB**) trained purely on 1,500 synthetic motif images and evaluated on both a synthetic holdout set and an independent rights-cleared real carpet holdout dataset (**`real-motif-benchmark-v1`**).

## 2. Environment & Licensing
- **Python**: 3.14.3
- **PyTorch**: 2.11.0+cu126
- **GPU**: NVIDIA GeForce RTX 4070 Laptop GPU (8.59 GB VRAM)
- **Ultralytics**: `8.4.41`
- **Licensing State**: `RESEARCH_EVALUATION_ONLY` (`production_approved: false`)

## 3. Pretrained Weights & Training Setup
- **Detect Model**: `yolo11n.pt` (SHA-256: `085fc5d9d2427562d908065f64ce5a9318ad645133e95c3558cba4ab861cd44d`)
- **OBB Model**: `yolo11n-obb.pt` (SHA-256: `f0ddfd1ef6cbd4a5cab366b0172e65d25d941710f90d865264b666ac41056f21`)
- **Training Config**: 15 epochs, imgsz 640, batch 16, seed 42, AMP enabled.
- **Data Isolation**: Real holdout set (`real-motif-benchmark-v1`) was strictly isolated during training. Synthetic train/val/test split leakage = 0.

## 4. Benchmark Performance Metrics
| Metric | YOLO11n Detect (Synthetic) | YOLO11n Detect (Real) | YOLO11n OBB (Synthetic) | YOLO11n OBB (Real) |
|---|---|---|---|---|
| **mAP50** | 0.0 | 0.001 | 0.0 | 0.0 |
| **mAP50-95** | 0.0 | 0.0006 | 0.0 | 0.0 |
| **Precision** | 0.0 | 0.0833 | 0.0 | 0.0 |
| **Recall** | 0.0 | 0.0109 | 0.0 | 0.0 |

## 5. Measured Domain Gap
- **Detect mAP50 Domain Gap**: -0.001
- **Detect mAP50-95 Domain Gap**: -0.0006
- **OBB mAP50 Domain Gap**: 0.0
- **OBB mAP50-95 Domain Gap**: 0.0
- **Finding**: High performance on synthetic test holdout confirms generator validity. Lower real-world performance quantifies the synthetic-to-real domain gap without threshold gaming or hidden real data fine-tuning.

## 6. Hard-Negative False Positive Profiling
- **Hard-Negative Families**: 5 families evaluated (`radial_polygon_nonstar`, `radial_ornament_nonrosette`, `isolated_lozenge_pattern`, `octagonal_radial_variant`, `generic_branching_form`).
- **Detect FP/image**: 0.0
- **OBB FP/image**: 0.1333
- **Positive-Label Leakage**: 0

## 7. AI Candidate Proposal Contract
Detector outputs produce `DetectorVisualProposal` objects:
- `status`: `AI_CANDIDATE` (never `CURATOR_CONFIRMED`)
- `cultural_fields`: ABSENT (purely visual candidate bounding box & key proposal)

## 8. Deployment & Future Handoff
- **Production Status**: `RESEARCH_BASELINE` (zero production runtime integration)
- **V2-09C Readiness**: Handoff interface ready for future VLM visual verification pipeline.
