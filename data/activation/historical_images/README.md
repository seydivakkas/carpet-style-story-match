# POST-v1 A8 / A8A / A8A.1 — Historical Local Image Activation & Terminal Accounting Closure

## Overview
This directory contains the activated historical local image sidecar dataset, activation report, and A8A/A8A.1 terminal accounting & provenance reconciliation reports.

## Run Accounting Models (A8A.1)
Each execution run maintains an independent terminal status accounting equation (`ACTIVATED + ALREADY_ACTIVE + RIGHTS_NOT_ELIGIBLE + other = total_considered`):
1. **Pilot Run** (`limit=5`):
   - `5 ACTIVATED + 0 ALREADY_ACTIVE + 0 RIGHTS_NOT_ELIGIBLE = 5 total` (Unaccounted: 0)
2. **Initial Full Activation Run** (First full run after pilot):
   - `40 ACTIVATED + 5 ALREADY_ACTIVE + 55 RIGHTS_NOT_ELIGIBLE = 100 total` (Unaccounted: 0)
3. **Idempotency Run** (Safe rerun after all 45 images active):
   - `0 ACTIVATED + 45 ALREADY_ACTIVE + 55 RIGHTS_NOT_ELIGIBLE = 100 total` (Unaccounted: 0)
4. **Final Terminal Database State**:
   - Historical References: 100
   - Historical Primary Images: 45
   - NO_PRIMARY_IMAGE: 55
   - STYLE_DNA_MISSING: 45

## Distinct Metrics & Hashes
1. **Source Image URL Metrics**:
   - `source_image_url_metadata_count`: Total historical records with recorded image URLs (45).
   - `eligible_source_image_url_count`: Open-access eligible records with recorded image URLs (45).
   - `local_primary_image_count`: Local binary images persisted and linked to database (45).
   - Note: Metadata URL != Eligible Image URL != Local Primary Image.

2. **Hash Disambiguation**:
   - `source_record_sha256`: SHA-256 hash of the normalized A6/A7 museum metadata/provenance snapshot record (Coverage: 100/100).
   - `image_content_sha256`: SHA-256 hash of the downloaded binary image payload (Coverage: 45/45 downloaded; null for 55 non-downloaded).
   - Note: Source-record snapshot hash != Downloaded image content hash.

## Files
- `historical-image-activation.json`: Ingestion sidecar dataset mapping historical references to storage keys, `source_record_sha256`, and `image_content_sha256`.
- `activation-report.json`: Execution report, run accounting telemetry, and readiness distribution.
- `a7-a8-rights-provenance-reconciliation.json`: A8A/A8A.1 closure report detailing rights resolution, run accounting equations, and hash coverage.
