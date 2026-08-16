# POST-v1 A9 — Historical Style DNA Batch Analysis

## Overview
This directory contains the batch run manifest, activation summary report, and README for POST-v1 A9 Historical Style DNA extraction.

## Core Rules & Architecture
1. **Algorithm Immutability**: Uses frozen `style-dna-v1.0.0` engine unchanged (no formula, threshold, or normalization changes).
2. **Historical Scope**: Strictly selects `CarpetModel.source_type == HISTORICAL` (100 historical references).
3. **Stored Binary Analysis**: Analyzes local binary image payloads stored in `ImageStorage` (0 remote downloads).
4. **Readiness Breakdown**:
   - `45` Image-Ready Historical References analyzed.
   - `55` `NO_PRIMARY_IMAGE` Historical References (V&A rights-review + Met non-open-access) preserved without analysis.
5. **Hash Linkage**:
   - `source_record_sha256`: A6/A7 museum metadata snapshot hash.
   - `image_content_sha256`: Local activated primary image binary SHA-256.
6. **Run Accounting**:
   - Pilot Run (`limit=5`): 5 processed (5 COMPLETE).
   - Initial Full Run: 40 processed + 5 already current + 55 no primary = 100 total.
   - Idempotency Run: 0 processed + 45 already current + 55 no primary = 100 total.
7. **A10 Boundary**: No `HistoricalConnection` records or recommendation scores generated in A9.

## Output Artifacts
- `style-dna-batch-run.json`: Batch manifest containing per-reference analysis records and provenance hashes.
- `activation-report.json`: Execution report, 9D dimension statistics, and final database readiness state.
