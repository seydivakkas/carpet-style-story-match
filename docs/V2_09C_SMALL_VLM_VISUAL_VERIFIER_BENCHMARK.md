# V2-09C — Small-VLM Visual Verifier Benchmark Specification & Preflight

## 1. Overview & Scientific Question
Following the V2-09B detector baseline evaluation (which identified a synthetic-to-real domain gap of mAP50 = 0.428), **V2-09C** evaluates small vision-language models (VLMs) as post-detector visual verifiers.

The scientific question for V2-09C is:
> *"Can a small visual-language verifier reduce false positives and visual-class mistakes from detector proposals without creating an unacceptable recall loss?"*

## 2. Frozen Verification Pipeline
```
Input Image ──► YOLO11n Proposal ──► Deterministic Input Compositor ──► Small VLM ──► ACCEPT / REJECT / ABSTAIN ──► Human Review
```
- **Visual Verification Only**: The VLM verifies geometric & feature match against the 17 visual candidate keys.
- **No Cultural Claims**: The VLM never outputs cultural, historical, symbolic, or regional claims.
- **No Curator Confirmation**: VLM ACCEPT status produces `AI_CANDIDATE` proposals only (never `CURATOR_CONFIRMED`).

## 3. Candidate Model Matrix
| Candidate ID | Model ID | Scale | Quantization | License | Preflight GPU Estimate | Download Status |
|---|---|---|---|---|---|---|
| **R0** | `Qwen/Qwen2.5-VL-3B-Instruct-AWQ` | 3B | AWQ INT4 | Apache-2.0 | `LIKELY_FITS` (~2.2 GB) | NOT_IN_LOCAL_CACHE |
| **C1** | `Qwen/Qwen3-VL-2B-Instruct` | 2B | Native FP16 | Apache-2.0 | `LIKELY_FITS` (~4.2 GB) | NOT_DOWNLOADED |
| **C2** | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` | 2.2B | Native FP16 | Apache-2.0 | `LIKELY_FITS` (~4.5 GB) | NOT_DOWNLOADED |
| **C3** | `Qwen/Qwen2-VL-2B-Instruct` | 2B | Native FP16 | Apache-2.0 | `LIKELY_FITS` (~4.2 GB) | NOT_DOWNLOADED |

### Excluded Models
- **PaliGemma** (`google/paligemma-3b-pt-224`): Excluded (`MANUAL_LICENSE_GATE` requiring Gemma terms acceptance).
- **SmolVLM2-500M / 256M**: Deferred (`EFFICIENCY_ABLATION` post-2B matrix comparison).

## 4. Model Download Approval Gate
- **Status**: `MODEL_DOWNLOAD_APPROVAL_REQUIRED`
- **Downloads Executed**: `false` (Zero weight files downloaded in V2-09C.0)
- **Preflight Storage**: 195.0 GB available (Estimated required: 15.1 GB -> PASS)

## 5. Visual Verifier Output Contract (`visual-verifier-v1.0.0`)
- **Decisions**: `ACCEPT`, `REJECT`, `ABSTAIN`
- **Allowed Visual Keys**: 17 frozen keys (`eight_pointed_star`, `geometric_rosette`, `stepped_polygon_medallion`, `latchhook_diamond`, `serrated_leaf`, `stylized_carnation`, `geometrized_tulip`, `tree_of_life_branching`, `comb_form`, `hands_on_hips_form`, `running_water_meander`, `hooked_lozenge`, `ram_horn_spiral`, `cross_star_variant`, `hexagonal_motif`, `star_medallion_composite`, `border_guard_stripe_element`)
- **Verified Key Rule**: `ACCEPT` may keep or correct the 17-key proposal. `REJECT` and `ABSTAIN` force `verified_visual_candidate_key = null`.
- **Strict Schema**: `additionalProperties: false` (unknown/cultural fields rejected).

## 6. Input Compositor (`visual-verifier-input-v1.0.0`)
- Concatenates full carpet context with green proposal rectangle (Left 336x448) and padded crop (Right 336x448) into a single 672x448 RGB image.
- Deterministic PNG SHA-256 hashing.

## 7. Evaluation Protocol & Three Benchmark Layers
1. **Synthetic Controlled Verification**: Evaluated on synthetic test holdout (positive + confusable + hard negatives).
2. **Real GT Controlled Verification**: Evaluated on 35 real images / 92 GT instances (`real-motif-benchmark-v1.0.0`).
3. **Actual Detector Proposal Verification**: Evaluated on proposals output by frozen YOLO11n Detect and OBB checkpoints.

## 8. Primary Metrics
- `schema_valid_rate`
- `coverage` = non_abstained_cases / total_cases
- `selective_accuracy` = correct_decisions / non_abstained_cases
- `hard_negative_rejection_rate`
- `precision_lift` = verified_precision - detector_precision
- `recall_cost` = detector_recall - verified_recall

## 9. Next Steps (V2-09C.1)
Execution of V2-09C.1 benchmark requires explicit user approval of the model download plan (`data/vlm/v2-09c-download-plan-v1.json`).
