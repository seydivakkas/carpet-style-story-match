# POST-v1 A8 — Historical Local Image Activation

## Overview
This directory contains the activated historical local image sidecar dataset and activation report for POST-v1 A8.

## Principles
1. **Rights-Aware Binary Ingestion**: Default mode `OPEN_ACCESS_ONLY` automatically ingests open-access/CC0 museum images (The Met 50) while respecting rights-review-required items (V&A 50).
2. **Standard Safe Image Pipeline**: Reuses exact application image validation (JPEG/PNG/WebP, 15MB size cap, 128px-12000px dimensions, EXIF orientation stripping, SHA-256 computation, `LocalImageStorage` persistence).
3. **Primary Image Linking**: Inserts `CarpetImageModel(is_primary=True)` on `CarpetModel(source_type=HISTORICAL)`.
4. **Readiness Transition**: Activated historical references transition from `NO_PRIMARY_IMAGE` -> `STYLE_DNA_MISSING`. Rights-restricted references remain `NO_PRIMARY_IMAGE`.
5. **DNA & Connection Boundary**: Zero Style DNA profiles are computed in A8 (deferred to A9). Zero Historical Connections are created in A8.
6. **Catalog Isolation**: Commercial Merinos catalog products (232) and catalog primary images (227) remain 100% unchanged.

## Files
- `historical-image-activation.json`: Ingestion sidecar dataset mapping historical references to storage keys & SHA-256 hashes.
- `activation-report.json`: Execution report, rights telemetry, and readiness distribution.
