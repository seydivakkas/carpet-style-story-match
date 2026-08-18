# V2-09 Final.1 — Full Catalog Motif Research Batch Report Integrity Closure

## Executive Summary
This document records the completion of V2-09 FINAL.1 Zero-Proposal Validation, Hash Provenance Reconciliation, Telemetry Audit, and Batch Report Integrity Closure.

Both frozen candidate detector streams (**Stream 1: YOLO11n Detect** and **Stream 2: YOLO11n OBB**) were executed in research-only mode over the complete processable commercial Merinos catalog (227 primary images out of 232 catalog products).

## Scientific Interpretation & Zero-Proposal Validation
- **Observed Results**: At the frozen 0.25 confidence threshold, both detector streams returned 227 successful `Results` objects and retained 0 proposals across all 227 processable catalog images.
- **Extractor Verification**: An extraction pipeline diagnostic smoke test on pre-existing synthetic test sample `syn_001277.jpg` verified that Detect (3 boxes) and OBB (7 boxes) correctly extract proposal DTOs, map class IDs `0..16` to frozen candidate keys, and process outputs. The catalog zero-proposal output is a genuine detector output at threshold 0.25.
- **Ground Truth & Metrics**: Because the commercial catalog dataset lacks complete motif ground truth annotations, zero retained proposals **does NOT establish precision, recall, false-positive rate, or motif absence**.
- **Domain Shift Warning**: The all-zero retained proposal rate may reflect domain shift between synthetic training data and real commercial catalog imagery, confidence calibration mismatch, limited detector generalization, or genuinely low confidence scores on catalog imagery.
- **Review Burden**: Observed automatic candidate-review workload at threshold 0.25 was zero. Zero review burden may come with an unknown or high missed-target burden.

## Hash Provenance Reconciliation
- **Visual Registry Hashes**:
  - `SERIALIZED_DICT_SHA256`: `05751c61fb5f8a6e1d5da2648bbb4a559722a5f6e7919bf2614d9d526371d35b` (SHA-256 of `load_class_map()` dict serialized key JSON).
  - `FILE_BYTES_SHA256`: `ba9c52acfe26fcbacf75a192b2598a15f33c057e9734e82c96831783f0fbd9e4` (SHA-256 of `data/synthetic/visual-candidate-class-map-v1.json` file bytes).
  - Both hash domains correspond to the exact same 17-key visual registry and exact `0..16` class ID mapping.
- **Input Manifest Hashes**:
  - `CANONICAL_MANIFEST_FINGERPRINT`: `43a20da8b6dc2448e04fbda83f4a37b8b0c2cba49fdda1a33b7c62e465d80eaf` (SHA-256 of canonical manifest payload dict).
  - `FILE_BYTES_SHA256`: `ef261386c22ab045fb65f4797ebd67bf912c165c35999573e1c98c29fa8bbfc3` (SHA-256 of formatted `catalog-motif-batch-input-manifest.json` on disk).

## Single Coherent Run Lineage & Telemetry
- **Batch Run ID**: `v2-09-final-catalog-20260818`
- **Detect Stream**: Attempted 227 / Successful 227 / Failed 0 / Wall Time: 3.79s / Mean Latency: 0.0165s/image
- **OBB Stream**: Attempted 227 / Successful 227 / Failed 0 / Wall Time: 3.07s / Mean Latency: 0.0134s/image
- **Detect Result Fingerprint**: `106e1fbc0c9955dfd3a956cf819a55e529fcf7ea44527a84c78d339fb92cb425`
- **OBB Result Fingerprint**: `6c73d539ff2852327ae67d51ba8dcb7b8be7c7e1bd427ef7d1e76a6e7119538c`

## CI & Acceptance Accounting
- **Pytest Suite**: 556 collected, 556 passed, 0 failed, 0 errors (`$LASTEXITCODE == 0`). `ENVIRONMENTAL_ATEXIT_CLEANUP_WARNING` captured for Windows `pytest-current` temp dir cleanup after test exit code 0.
- **Frontend App**: `npm run typecheck` (PASS), `npm run lint` (PASS), `npm run build` (PASS: Generating static pages 9/9, 17 app routes built).
- **Validation Benchmark Runner**: 57/57 PASS.
- **Make Check Emulation**: Exit Code 0 (PASS).

## Data Isolation & VLM Accounting
- **Full Catalog VLM Calls**: 0
- **New Closure VLM Calls**: 0
- **Production DB Writes**: 0
- **Cultural Claims Generated**: 0
- **Stories Generated**: 0
- **Auto Human Confirmations**: 0
- **Single Detector Winner Selected**: None

