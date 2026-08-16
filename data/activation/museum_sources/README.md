# POST-v1 A6 — Museum Source Activation Pipeline

## Overview
This directory contains the official object-level museum source registry, normalized object dataset, and activation reports for POST-v1 A6.

## Principles
1. **Official Museum Sources Only**: Ingests official object records from The Metropolitan Museum of Art and the Victoria and Albert Museum.
2. **Stable Object-Level Identifiers**: Every record requires a stable institutional object ID (`objectID` or `systemNumber`).
3. **Strict Object Identity Filtering**: Accepts only genuine carpet/rug/textile floor covering objects; search false positives (paintings depicting carpets, books, photographs) are rejected (`REJECTED_NOT_CARPET`).
4. **Source-Reported Metadata Only**: No culture, period, dynasty, or date guessing. Unknown values remain `null`.
5. **Rights Separation**: Metadata usability (`METADATA_USABLE`) is strictly separated from image reuse permission (`IMAGE_REUSE_ALLOWED`).
6. **No Image Binary Downloads**: Image reference URLs and IIIF endpoints are captured for metadata provenance, but zero image binaries are downloaded in A6 (deferred to A8).
7. **Strict A7 Boundary**: Creates validated `CuratedSource(source_type=MUSEUM_OBJECT)` records in the database, but **0** `HistoricalReferenceMetadata` or `CarpetModel` historical rows are created (deferred to A7).

## Files
- `registry.json`: Official institutional provider registry (`met`, `vam`).
- `museum-object-sources.json`: Normalized factual object dataset.
- `rejected-candidates.json`: Provenance log of rejected non-carpet search results.
- `activation-report.json`: Execution metrics and database delta summary.
