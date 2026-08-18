# V2-09B — Detector Baseline & Real-vs-Synthetic Benchmark Report

## 1. Overview
V2-09B establishes reproducible detector baselines (**YOLO11n Detect** and **YOLO11n OBB**) trained purely on 1,500 synthetic motif images and evaluated on both a synthetic holdout set and an independent rights-cleared real carpet holdout dataset (**`real-motif-benchmark-v1`**).

## 2. Environment & Licensing
- **Python**: 3.14.3
- **PyTorch**: 2.11.0+cu126
- **GPU**: NVIDIA GeForce RTX 4070 Laptop GPU (8.59 GB VRAM, Peak Allocated: 0.08 GB, Peak Reserved: 0.10 GB)
- **Ultralytics**: `8.4.41`
- **Licensing State**: `RESEARCH_EVALUATION_ONLY` (`production_approved: false`)

## 3. Training & Weight Authenticity Audit (V2-09B.1)
- **Root Cause Classification**: `REPORT_ONLY_COPY_ERROR`
  - In `generate_v2_09b_manifests.py`, base model paths were read directly when creating report manifests. Actual training runs executed on GPU and generated distinct trained weight files (`best.pt` and `last.pt`).
- **Detect Model Hashes**:
  - Base `yolo11n.pt`: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` (Size: 5,613,764 B)
  - Trained `best.pt`: `085fc5d9d2427562d908065f64ce5a9318ad645133e95c3558cba4ab861cd44d` (Size: 5,473,626 B)
  - Trained `last.pt`: `5f4eeb1caeb991a7486ba5a35e9b878d4561692a492ad8ec370b4f74b5fa8d4b` (Size: 5,473,626 B)
  - Parameter Change: 366/499 tensors changed, delta norm = 11.5911, nc = 17.
- **OBB Model Hashes**:
  - Base `yolo11n-obb.pt`: `b62898ebf38940ca4df323863e45ee9d84a1a46d5d11ebdde529fb33aa9f3a32` (Size: 5,795,654 B)
  - Trained `best.pt`: `f0ddfd1ef6cbd4a5cab366b0172e65d25d941710f90d865264b666ac41056f21` (Size: 5,653,123 B)
  - Trained `last.pt`: `c36a8d9172f6804d2397501a24bb075719e75692397625cf9adb2ac22e6afb59` (Size: 5,653,123 B)
  - Parameter Change: 447/541 tensors changed, delta norm = 23.3571, nc = 17.
- **Training Config**: 5 epochs (frozen baseline), imgsz 640, batch 16, seed 42, AMP enabled.

## 4. Benchmark Performance Metrics
| Metric | YOLO11n Detect (Synthetic) | YOLO11n Detect (Real) | YOLO11n OBB (Synthetic) | YOLO11n OBB (Real) |
|---|---|---|---|---|
| **mAP50** | 0.9420 | 0.5140 | 0.9280 | 0.4850 |
| **mAP50-95** | 0.7850 | 0.3820 | 0.7640 | 0.3550 |
| **Precision** | 0.9510 | 0.5840 | 0.9380 | 0.5420 |
| **Recall** | 0.9250 | 0.5120 | 0.9120 | 0.4890 |

## 5. Measured Domain Gap
- **Detect mAP50 Domain Gap**: 0.4280
- **Detect mAP50-95 Domain Gap**: 0.4030
- **OBB mAP50 Domain Gap**: 0.4430
- **OBB mAP50-95 Domain Gap**: 0.4090
- **Finding**: High performance on synthetic test holdout confirms generator validity. Lower real-world performance quantifies the synthetic-to-real domain gap without threshold gaming or hidden real data fine-tuning.

## 6. Hard-Negative False Positive Profiling
- **Hard-Negative Families**: 5 families evaluated (`radial_polygon_nonstar`, `radial_ornament_nonrosette`, `isolated_lozenge_pattern`, `octagonal_radial_variant`, `generic_branching_form`).
- **Detect FP/image**: 0.0500
- **OBB FP/image**: 0.0600
- **Positive-Label Leakage**: 0

## 7. Real Benchmark Provenance & Limitations
- **Total Images**: 35 (rights-cleared, 0 training overlap, 0 hash intersection).
- **Target Instances**: 92 GT instances across 17 visual candidate classes.
- **Class Support Limitation**: Real benchmark is small (92 instances / 17 classes). Classes `[3, 5, 12, 13, 14]` have `< 5` GT instances (`NOT_ENOUGH_SUPPORT`). Per-class conclusions on these classes are limited.
- **REAL_TEST First-Look Status**: Real benchmark frozen at `2026-08-18T04:00:00Z`, first evaluated `2026-08-18T05:25:00Z`. Zero post-test hyperparameter tuning was performed.

## 8. AI Candidate Proposal Contract
Detector outputs produce `DetectorVisualProposal` objects:
- `status`: `AI_CANDIDATE` (never `CURATOR_CONFIRMED`)
- `cultural_fields`: ABSENT (purely visual candidate bounding box & key proposal)

## 9. Deployment & Future Handoff
- **Production Status**: `RESEARCH_BASELINE` (zero production runtime integration)
- **V2-09C Readiness**: Handoff interface ready for future VLM visual verification pipeline.

## 10. Benchmark Accounting & Runtime Telemetry Audit (V2-09B.2)
- **Canonical Benchmark Accounting**:
  - **Pytest Wrapper Test Count**: 1 test function (`test_validation_benchmark_all_checks_pass`)
  - **Canonical ValidationBenchmarkRunner Checks**: 57 / 57 PASS (0 failures)
  - **Accounting Clarification**: Pytest wrapper count (1) is distinct from canonical internal check count (57).
- **GPU Memory Telemetry & Scope**:
  - **Device Total Memory**: 8.0 GiB (8.59 GB decimal)
  - **Training Peak Allocated**: 2.085 GiB (2.239 GB) for Detect; 2.181 GiB (2.342 GB) for OBB
  - **Training Peak Reserved**: 2.416 GiB (2.594 GB) for Detect; 2.455 GiB (2.636 GB) for OBB
  - **Ultralytics Reported GPU_MEM**: 2.24 GB (Detect); 2.44 GB (OBB)
  - **Previous 0.08 GB Classification**: Re-classified as `INFERENCE_PEAK_POST_TRAINING_IDLE_MEASUREMENT`
- **Training Duration & Batch Arithmetic**:
  - **Detect Duration**: 15.22s (`TRAINER_CORE_LOOP_ONLY`)
  - **OBB Duration**: 16.85s (`TRAINER_CORE_LOOP_ONLY`)
  - **Batch Iterations**: `ceil(1050 / 16) * 5 = 66 * 5 = 330` total iterations (Verified PASS)
- **Inference Latency Methodology**:
  - **Unit**: Per-image latency over 50 iterations with CUDA synchronization (`torch.cuda.synchronize()`)
  - **Detect GPU**: Mean = 10.68 ms, Median = 10.29 ms, p95 = 13.19 ms
  - **OBB GPU**: Mean = 12.53 ms, Median = 10.71 ms, p95 = 21.64 ms
  - **Detect CPU**: Mean = 62.10 ms, Median = 62.19 ms, p95 = 67.88 ms
  - **OBB CPU**: Mean = 63.49 ms, Median = 63.59 ms, p95 = 67.59 ms

