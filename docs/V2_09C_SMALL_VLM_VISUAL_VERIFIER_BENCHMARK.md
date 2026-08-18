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
- Candidates C1, C2, C3 are fully `RUNTIME_READY`.
- Candidate R0 is excluded (`RUNTIME_INCOMPATIBLE`) due to Python 3.14 AWQ compilation constraints.

## 10. V2-09C.1B — Corrected Smoke Execution Provenance & Identity Audit
- **Root Cause Audit**: Models C1/C2/C3 genuinely regenerated outputs containing `17-001`/`geometrized_tulip`, `1`/`geometric_rosette`, and `1234567890`/`latchhook_diamond` because the frozen prompt text (`f8417b31...`) contains a list of 17 candidate keys and JSON placeholders (`<proposal_id>`, `<proposed_key>`). Without system prompt template substitution (disallowed under prompt immutability), zero-shot VLMs populated placeholders with keys listed in the prompt body.
- **Provenance Verification**:
  - `stale_response_reuse`: `false`
  - `fixture_response_reuse`: `false`
  - `model_response_cache`: `false`
  - `old_defective_strings_in_active_prompt`: `false`
- **Trusted Identity Separation**: Model-emitted proposal IDs and visual candidate keys are treated as untrusted validation fields. Authoritative downstream provenance joins rely strictly on trusted input records (`VerifierRuntimeInputRecord`).
## 11. V2-09C.1C — Deterministic Prompt Binding & Benchmark Freeze

### Prompt Materializer & Semantic Identity Binding
- **Component**: `VisualVerifierPromptMaterializer` (`visual-verifier-prompt-materializer-v1.0.0`).
- **Prompt Template Hash**: `f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac` (UNALTERED).
- **Materialized Prompt Hash**: `981ebe0cd2d5ff23da160c49c09fcda04e198e36bd62372b8bd600bb50053d84`.
- **Canonical Semantic Payload Hash**: `981ebe0cd2d5ff23da160c49c09fcda04e198e36bd62372b8bd600bb50053d84`.
- **Materialization Behavior**:
  - Replaces `<proposal_id>` with trusted proposal ID (`smoke_001`).
  - Replaces `<proposed_key>` with trusted visual key (`star_like`).
  - Enforces pre-inference validation: proposal ID must match `^[a-zA-Z0-9_-]{1,64}$` and proposed key must be one of the frozen 17 visual candidate keys. Non-17 keys (e.g. `geometrized_tulip`) or domain terms (e.g. `elibelinde`) raise `ValueError` prior to model invocation.

### Benchmark Freeze Artifact (`visual-verifier-benchmark-freeze.json`)
- **Location**: `data/validation/v2-09c/visual-verifier-benchmark-freeze.json`
- **Schema Hash**: `aa63efd246a867f84ba931900589343fc080f18f6dab2155552bac10d41547f8`
- **Prompt Template Hash**: `f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac`
- **Compositor Hash**: `6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d`
- **Eligible Benchmark Models**: `C1` (`Qwen/Qwen3-VL-2B-Instruct`), `C2` (`SmolVLM2-2.2B-Instruct`), `C3` (`Qwen2-VL-2B-Instruct`)
- **Excluded Models**: `R0` (`Qwen2.5-VL-3B-Instruct-AWQ` - `RUNTIME_INCOMPATIBLE`)
- **REAL_TEST VLM Calls**: **0** (REAL_TEST strictly unopened)
- **Status**: `PASS_WITH_RUNTIME_EXCLUSIONS`

## 12. V2-09C.2 / V2-09C.2A — Frozen Small-VLM Visual Verifier Benchmark Execution & Result Accounting

### First-Look Audit Boundary & Zero New Calls
- **REAL_TEST Opened At**: `2026-08-18T08:18:27Z`
- **First Evaluated Model**: Candidate `C1`
- **First-Look Audit Artifact**: `data/validation/v2-09c/real-test-first-look-audit.json`
- **Scientific Accounting Audit**: `data/validation/v2-09c/benchmark-result-accounting-audit.json`
- **Pre-Run Freeze Verification**: `PASS`
- **Post-Open Modifications**: `NONE`
- **Historical REAL_TEST VLM Call Count**: **474** (158 real test cases * 3 eligible candidates)
- **Post-Benchmark New VLM Calls**: **0** (No new inference executed in V2-09C.2A)
- **Post-Benchmark Tuning**: `false` (REAL_TEST strictly preserved as frozen test boundary)

### Manifest Case Counts & Denominators
| Benchmark Layer | Case Count | Manifest Hash (SHA-256) |
|---|---|---|
| **Layer A: Synthetic Controlled Verification** | 128 | `ff2c4ae5536ee6dc3dfe497e826973c59de307f9addde47bcb7a7a7f6dbcdeac` |
| **Layer B: Real GT Controlled Verification** | 109 | `283d86bf848dee3fd7f981622995ac542b35d8dede65c5b9bcea065fc1c7e0f8` |
| **Layer C1: Detector Proposals (YOLO11n Detect)** | 12 | `fae53fe08ece778b4a821e291f08f8b38df60904f9a8b07d275fece7554598ee` |
| **Layer C2: Detector Proposals (YOLO11n OBB)** | 37 | `25e1a14ecfa2a5d08e92d6a30e94d2c60af1448629ec793b96e603a7620d18d9` |
| **Total Cases Per Candidate** | **286** | -- |

### Comprehensive Multi-Metric Comparison Matrix (No Ranking Assigned)

| Metric / Evaluation Dimension | C1: Qwen3-VL-2B-Instruct | C2: SmolVLM2-2.2B-Instruct | C3: Qwen2-VL-2B-Instruct | R0: Qwen2.5-VL-3B-AWQ |
|---|---|---|---|---|
| **Evaluation Status** | `EVALUATED` | `EVALUATED` | `EVALUATED` | `EXCLUDED` (`RUNTIME_INCOMPATIBLE`) |
| **Load Time / Peak Memory** | 3.46s / 3.994 GiB | 5.84s / 4.217 GiB | 5.08s / 4.147 GiB | N/A |
| **Mean Latency / P95 Latency** | 4.855s / 5.547s | 3.444s / 3.858s | 5.290s / 6.273s | N/A |
| **Peak Infer Memory (Alloc / Res)** | 4.186 GiB / 4.209 GiB | 4.633 GiB / 4.727 GiB | 4.269 GiB / 4.312 GiB | N/A |
| **Layer A: Schema Valid Rate** | 5.47% (7/128) | 34.38% (44/128) | 26.56% (34/128) | N/A |
| **Layer A: Semantic Valid Rate** | 3.91% (5/128) | 33.59% (43/128) | 23.44% (30/128) | N/A |
| **Layer A: Coverage** | 3.91% (5/128) | 33.59% (43/128) | 23.44% (30/128) | N/A |
| **Layer A: Selective Accuracy** | 80.0% (4/5 support) | 72.09% (31/43 support) | 63.33% (19/30 support) | N/A |
| **Layer A: Correct-Key Accuracy** | 100.0% (4/4) | 88.57% (31/35) | 95.00% (19/20) | N/A |
| **Layer A: False Accept Rate** | 3.85% (1/26) | 30.77% (8/26) | 38.46% (10/26) | N/A |
| **Layer A: Hard-Negative Rejection** | 0.0% (0/20) | 0.0% (0/20) | 0.0% (0/20) | N/A |
| **Layer B: Schema Valid Rate** | 13.76% (15/109) | 23.85% (26/109) | 12.84% (14/109) | N/A |
| **Layer B: Semantic Valid Rate** | 3.67% (4/109) | 23.85% (26/109) | 11.93% (13/109) | N/A |
| **Layer B: Coverage** | 3.67% (4/109) | 23.85% (26/109) | 11.93% (13/109) | N/A |
| **Layer B: Selective Accuracy** | 75.0% (3/4 support) | 76.92% (20/26 support) | 84.62% (11/13 support) | N/A |
| **Layer C1 (Detect): Precision (Before -> After)** | 0.0833 -> 0.0000 | 0.0833 -> 0.2500 | 0.0833 -> 0.0000 | N/A |
| **Layer C1 (Detect): Precision Lift** | -0.0833 (-8.33%) | +0.1667 (+16.67%) | -0.0833 (-8.33%) | N/A |
| **Layer C1 (Detect): Recall (Before -> After)** | 0.0109 -> 0.0000 | 0.0109 -> 0.0109 | 0.0109 -> 0.0000 | N/A |
| **Layer C1 (Detect): Recall Cost** | 0.0109 (1.09%) | 0.0000 (0.0%) | 0.0109 (1.09%) | N/A |
| **Layer C1 (Detect): FP / Image (Before -> After)** | 0.3143 -> 0.0000 | 0.3143 -> 0.0857 | 0.3143 -> 0.0000 | N/A |
| **Layer C2 (OBB): Precision (Before -> After)** | 0.0000 -> 0.0000 | 0.0000 -> 0.0000 | 0.0000 -> 0.0000 | N/A |
| **Layer C2 (OBB): Precision Lift** | 0.0000 (0.0%) | 0.0000 (0.0%) | 0.0000 (0.0%) | N/A |
| **Layer C2 (OBB): Recall (Before -> After)** | 0.0000 -> 0.0000 | 0.0000 -> 0.0000 | 0.0000 -> 0.0000 | N/A |
| **Layer C2 (OBB): Recall Cost** | 0.0000 (0.0%) | 0.0000 (0.0%) | 0.0000 (0.0%) | N/A |
| **Layer C2 (OBB): FP / Image (Before -> After)** | 1.0571 -> 0.0000 | 1.0571 -> 0.7143 | 1.0571 -> 0.2000 | N/A |
| **Layer C2 (OBB): FP / Image Δ** | -1.0571 | -0.3428 | -0.8571 | N/A |

### Scientific Findings & Pareto Observations (No Ranking Assigned)
1. **Structured Output Non-Compliance**:
   Schema validity was low, corresponding to high structured-output non-compliance (65.62% to 94.53% invalid schema outputs across candidates under zero-shot greedy decoding).
2. **Hard-Negative Limitation**:
   None of the evaluated zero-shot candidates demonstrated reliable explicit hard-negative rejection under the frozen verifier contract (0/20 explicit rejection across C1, C2, and C3).
3. **Pareto-Style Multi-Metric Observations**:
   - **C2 (`SmolVLM2-2.2B-Instruct`)** exhibited the highest observed schema validity (34.38% synthetic, 23.85% real GT).
   - **C3 (`Qwen2-VL-2B-Instruct`)** achieved higher real controlled selective accuracy (84.62%) than C1 (75.0%) and C2 (76.92%), but on a smaller support (13/109 valid non-abstained cases vs 26/109 for C2).
   - **C2** demonstrated positive Detect precision lift (+16.67% from 0.0833 to 0.25) with zero measured recall loss at the frozen 12-proposal operating point.
   - **C1 (`Qwen3-VL-2B-Instruct`)** exhibited the lowest model load peak memory (3.994 GiB).
   - **C2** had the lowest measured mean inference latency (3.444s vs 4.855s for C1 and 5.290s for C3).
4. **Dominant Limitation & Future Experiments**:
   - Dominant limitation category: `OUTPUT_CONFORMANCE_DOMINANT_LIMITATION`.
   - Constrained decoding is a plausible future experiment because schema validity was low, corresponding to high structured-output non-compliance.
   - QLoRA fine-tuning status: `NOT_YET_JUSTIFIED`.
   - REAL_TEST boundary strictly frozen: REAL_TEST cannot be used for iterative prompt or grammar optimization.

### Final Task Closure Status
**STATUS**: `PASS_RESULT_CLOSURE`
- Result artifact: `data/validation/v2-09c/small-vlm-benchmark-result-v1.json`
- Audit artifact: `data/validation/v2-09c/benchmark-result-accounting-audit.json`
- First-look audit: `data/validation/v2-09c/real-test-first-look-audit.json`
- Freeze definition: `data/validation/v2-09c/visual-verifier-benchmark-freeze.json`



