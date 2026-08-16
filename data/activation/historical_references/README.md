# POST-v1 A7 — Historical Reference Dataset Activation

## Overview
This directory contains the official activated historical reference dataset and promotion report for POST-v1 A7.

## Principles
1. **Official Museum Object Promotion**: Promotes A6 validated `MUSEUM_OBJECT` sources into the historical reference collection (`CarpetModel(source_type=HISTORICAL)`).
2. **1:1 Historical Metadata**: Each record links 1:1 to `HistoricalReferenceMetadataModel` and `HistoricalReferenceSourceModel(role=PRIMARY_OBJECT_RECORD)`.
3. **Exact Primary Provenance**: Exactly 1 primary museum object source per historical reference.
4. **Source-Reported Metadata Only**: No guessing of culture, period, dynasty, or numerical date ranges (`date_start_year` & `date_end_year` are null unless explicitly provided in structured form).
5. **Image & Style DNA Isolation**: Metadata image references (`source_image_url`) are stored for preview only; zero image binaries are downloaded and zero `CarpetImage` rows are created (deferred to A8). Zero Style DNA profiles are generated (deferred to A9).
6. **Catalog Isolation**: Commercial Merinos catalog (232 products) remains 100% isolated and unchanged.

## Files
- `historical-references.json`: Activated historical reference curation dataset (`historical-reference-curation-v1`).
- `activation-report.json`: Execution metrics, database delta, and A8 planning telemetry.
