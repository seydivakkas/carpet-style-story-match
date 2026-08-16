# POST-v1 A8 / A8A — Historical Local Image Activation & Rights Provenance Closure

## Overview
This directory contains the activated historical local image sidecar dataset, activation report, and A8A rights & source-hash provenance reconciliation report.

## Distinct Metrics & Hashes
1. **Source Image URL Metrics**:
   - `source_image_url_metadata_count`: Total historical records with recorded image URLs (45).
   - `eligible_source_image_url_count`: Open-access eligible records with recorded image URLs (45).
   - `local_primary_image_count`: Local binary images persisted and linked to database (45).
   - Note: Metadata URL != Eligible Image URL != Local Primary Image.

2. **Hash Disambiguation**:
   - `source_record_sha256`: SHA-256 hash of the normalized A6/A7 museum metadata/provenance snapshot record (Coverage: 100/100).
   - `image_content_sha256`: SHA-256 hash of the downloaded binary image payload payload (Coverage: 45/45 downloaded; null for 55 non-downloaded).
   - Note: Source-record snapshot hash != Downloaded image content hash.

## Rights Reconciliation (A8A)
- **Outcome**: CASE A — A7 summary text reported 50 open-access Met records by approximation, but the factual underlying A6/A7 dataset (`museum-object-sources.json` / `a7-input-snapshot.json`) contained 45 open-access CC0 records and 5 non-open-access "All Rights Reserved" records.
- **5 Met Exceptions**: Object IDs `489476`, `452575`, `456972`, `450571`, `452370` have `open_access: false`, `rights_statement: "All Rights Reserved"`, `source_image_url: null`.
- **Terminal Status Accounting**: 45 Eligible (40 ACTIVATED + 5 ALREADY_ACTIVE) + 55 RIGHTS_NOT_ELIGIBLE (5 Met + 50 V&A) = 100 total.

## Files
- `historical-image-activation.json`: Ingestion sidecar dataset mapping historical references to storage keys, `source_record_sha256`, and `image_content_sha256`.
- `activation-report.json`: Execution report, rights telemetry, and readiness distribution.
- `a7-a8-rights-provenance-reconciliation.json`: A8A closure report detailing 50->45 rights resolution, URL metrics, and hash coverage.
