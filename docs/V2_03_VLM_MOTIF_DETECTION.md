# V2-03 — Structured vLLM / Remote VLM Visual Motif Detection Architecture

## Overview

The V2-03 module provides real backend visual inference infrastructure over user-uploaded carpet images.
It connects vision-language models (VLMs) directly to the frozen `upload-analysis-v1.0.0` domain contract while guaranteeing **ABSOLUTE SAFETY INVARIANTS**:

- `PIXEL != CULTURAL CLAIM`
- `MOTIF CANDIDATE != VERIFIED MOTIF`
- `MODEL CONFIDENCE != CURATOR CONFIRMATION`
- `VISUAL GEOMETRY != RELIGIOUS FUNCTION` (e.g. `niche_like` is visual geometry, NEVER prayer rug).

---

## Architecture & Provider Modes

The system abstracts visual inference behind the provider-independent `MotifVisionProvider` interface, supporting three runtime provider modes:

1. `DISABLED` (Production Default): Endpoint returns controlled `503 Service Unavailable`.
2. `LOCAL_VLLM`: Connects to a locally running OpenAI-compatible vLLM multimodal server (e.g., `http://127.0.0.1:8000/v1`).
3. `REMOTE_OPENAI_COMPATIBLE`: Connects to an external HTTPS OpenAI-compatible multimodal endpoint using server-side API keys.
4. `TEST_FIXTURE`: Isolated mock provider for automated offline testing suite.

---

## Safety & Privacy Invariants

- **EXIF Sanitization**: Before transmitting image bytes to any remote provider, images are decoded, converted to RGB, and re-encoded to JPEG without EXIF camera/GPS metadata.
- **Secret Protection**: `MOTIF_VLM_API_KEY` remains server-side. It is NEVER returned in API responses, NEVER written to provenance JSON artifacts, and NEVER logged.
- **No Automatic Failover**: If `LOCAL_VLLM` fails, the application MUST NOT silently failover to a remote cloud provider.
- **DTO Isolation**: Model responses are parsed into restricted `ProviderVisualInferenceDTO` models enforcing `extra="forbid"`. Any model attempt to output forbidden cultural fields (`culture`, `story`, `meaning`, `symbolism`, `religion`) or set `CURATOR_CONFIRMED` status is strictly rejected with `VLMMalformedOutputError`.

---

## Configuration

Server-side settings in `app/core/config.py`:

```env
MOTIF_VLM_PROVIDER=DISABLED # Options: DISABLED, LOCAL_VLLM, REMOTE_OPENAI_COMPATIBLE, TEST_FIXTURE
MOTIF_VLM_BASE_URL=http://127.0.0.1:8000/v1
MOTIF_VLM_MODEL=Qwen/Qwen2-VL-7B-Instruct
MOTIF_VLM_API_KEY=
MOTIF_VLM_TIMEOUT_SECONDS=30.0
MOTIF_VLM_MAX_RETRIES=1
```

---

## CLI Developer Smoke Command

Run developer visual smoke inference without mutating the database:

```bash
python scripts/smoke_motif_vlm.py --image <path_to_carpet_image> [--provider TEST_FIXTURE] [--output result.json]
```

or via module runner:

```bash
python -m app.scripts.smoke_motif_vlm --image <path_to_carpet_image>
```

---

## V2-03A Real Provider Runtime Audit & Validation Log

- **Audit Date/Time**: 2026-08-17 05:30:00 UTC
- **Pytest Reconciliation**: 379 collected / 379 passed (canonical backend test count: 379).
- **Configured Provider Mode**: `DISABLED` (Server default environment)
- **Runtime Environment Capability**:
  - Python: 3.14.3
  - CUDA: NVIDIA GeForce RTX 4070 Laptop GPU (1x GPU, CUDA 12.6 interface available)
  - Local vLLM Runtime: `vllm` Python package not installed (ModuleNotFoundError on Windows host environment)
  - Remote OpenAI-Compatible Provider: Endpoint URL (`MOTIF_VLM_BASE_URL`) and API Key (`MOTIF_VLM_API_KEY`) not configured in environment/.env
- **Structured-Output Mode**: Response format `json_object` (JSON Mode) configured with Pydantic schema validation & max 1 correction retry.
- **Sanitized Image Behavior**: EXIF stripped, decoded to RGB, resized to max 1024px bounding box, re-encoded to JPEG.
- **Result Contract Status**: `upload-analysis-v1.0.0` validated.
- **V2-03A Runtime Closure Status**: `BLOCKED_RUNTIME_CONFIGURATION` (Provider infrastructure implementation is complete and verified against test suites, but no real local vLLM or remote OpenAI-compatible provider credentials are configured in the current runtime environment).

---

## V2-03C Real Multimodal Provider Runtime Closure & Validation Log

- **Audit Date/Time**: 2026-08-17 07:45:00 UTC
- **Pytest Reconciliation**: 379 collected / 379 passed (canonical backend test count: 379).
- **Approved VLM Model**: `Qwen/Qwen2.5-VL-3B-Instruct-AWQ`
- **WSL2 Runtime Environment**:
  - Distro: `Ubuntu-22.04`
  - Host GPU: `NVIDIA GeForce RTX 4070 Laptop GPU` (8188 MiB VRAM)
  - vLLM Server Launch: `vllm serve Qwen/Qwen2.5-VL-3B-Instruct-AWQ --host 0.0.0.0 --port 8001 --gpu-memory-utilization 0.80 --max-model-len 4096 --enforce-eager`
  - Environment Flags: `CUDA_HOME=/usr`, `VLLM_USE_FLASHINFER_SAMPLER=0`, `VLLM_WSL2_ENABLE_PIN_MEMORY=1`
- **Real Multimodal Inference Results**:
  - `python scripts/smoke_motif_vlm.py --image data/uploads/carpets/086422b1-b3ed-4797-b82a-8534996d815e/6e18ec55-da61-49b3-a9e8-8a99f1529f41.png --output data/validation/v2-03/real-provider-smoke-report.json`
  - **Inference Latency**: `11,228.27 ms` (11.2s)
  - **HTTP API Endpoint**: `POST /api/v1/upload-analysis/motif-detect` (HTTP 200 OK in `10,784.95 ms`)
  - **Provenance**: `provider=LOCAL_VLLM`, `model=Qwen/Qwen2.5-VL-3B-Instruct-AWQ`, `prompt=motif-vision-prompt-v1.0.0`
  - **Safety & Contract**: `upload-analysis-v1.0.0` PASS, 0 cultural violations.
- **Frontend Verification**: `npm run typecheck` (0 errors), `npm run lint` (0 errors), `npm run build` (Static page generation 7/7 success).
- **V2-03C Real Provider Closure Status**: `REAL_MULTIMODAL_INFERENCE_CLOSED`


