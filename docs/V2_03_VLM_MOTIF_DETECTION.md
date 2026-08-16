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
