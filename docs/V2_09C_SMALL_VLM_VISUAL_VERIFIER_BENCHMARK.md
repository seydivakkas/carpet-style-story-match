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

## 8. V2-09C.1 — Model Download & Sequential Runtime Smoke Results

### Download Provenance & Artifact Hashes
- **Download Approval**: Approved for R0, C1, C2, C3.
- **Downloaded Repositories**: 4 / 4
- **Measured Total Storage**: 19.656 GB (Free disk remaining: > 175 GB)
- **REAL_TEST VLM Calls**: **0** (REAL_TEST strictly unopened)

| Candidate | Model Repository ID | HF Revision SHA | Snapshot Manifest SHA-256 | Size (GiB) | Weight Shards | Runtime Status | Dtype |
|---|---|---|---|---|---|---|---|
| **R0** | `Qwen/Qwen2.5-VL-3B-Instruct-AWQ` | `e7b623934290c5a4da0ee3c6e1e57bfb6b5abbf2` | `97824d4a1d48e483f08fc020b75c4e2dc52de8e2d262000821e9b6ff55de8685` | 3.183 | 1 (`model.safetensors`) | `RUNTIME_INCOMPATIBLE` | N/A |
| **C1** | `Qwen/Qwen3-VL-2B-Instruct` | `89644892e4d85e24eaac8bacfd4f463576704203` | `ccc27a55974c4e0072ba449dc4163a35b5fa9a498410c9831341bdc7c60d227c` | 3.974 | 1 (`model.safetensors`) | `RUNTIME_READY` | `bfloat16` |
| **C2** | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` | `482adb537c021c86670beed01cd58990d01e72e4` | `f7568e5a761aa064db58bb09f8a4e4e4a8124993f0939c6d73c794ef9162fcdd` | 8.375 | 2 (`model-00001..2`) | `RUNTIME_READY` | `bfloat16` |
| **C3** | `Qwen/Qwen2-VL-2B-Instruct` | `895c3a49bc3fa70a340399125c650a463535e71c` | `5ddb0cedc195ecf4b7f401804855f3d7e8e5349ce970e769ac2e6d7e619e8e4a` | 4.125 | 2 (`model-00001..2`) | `RUNTIME_READY` | `bfloat16` |

### Sequential Runtime Smoke Telemetry

- **Golden Compositor Input**: `data/validation/v2-09c/golden_smoke_input.png` (SHA-256: `6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d`)
- **Prompt Hash**: `data/vlm/prompts/motif-visual-verifier-prompt-v1.txt` (SHA-256: `f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac`)

| Candidate | Load Time (s) | Load Peak Alloc (GiB) | Infer Time (s) | Infer Peak Alloc (GiB) | Infer Peak Reserved (GiB) | Gen Tokens | Schema Valid | Status |
|---|---|---|---|---|---|---|---|---|
| **R0** | N/A | N/A | N/A | N/A | N/A | 0 | `False` | `RUNTIME_INCOMPATIBLE` (AWQ C-extension build failed on Py3.14 Windows) |
| **C1** | 4.40 | 3.963 | 5.73 | 4.164 | 4.189 | 120 | `True` | `RUNTIME_READY` |
| **C2** | 3.19 | 4.195 | 3.24 | 4.610 | 4.672 | 106 | `True` | `RUNTIME_READY` (Requires `num2words==0.5.14`) |
| **C3** | 4.70 | 4.124 | 4.62 | 4.247 | 4.287 | 107 | `True` | `RUNTIME_READY` |

## 9. V2-09C.1 Final Acceptance Status
**STATUS**: `PASS_WITH_RUNTIME_EXCLUSIONS`
- Candidates C1, C2, C3 are fully `RUNTIME_READY` and schema compliant (`visual-verifier-v1.schema.json`).
- Candidate R0 is excluded (`RUNTIME_INCOMPATIBLE`) due to Python 3.14 AWQ compilation constraints.
