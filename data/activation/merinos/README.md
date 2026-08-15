# Merinos Catalog Activation Dataset v1 (Post-v1 A1 & A2)

## Overview & Provenance Notice

- **Origin**: All product metadata and image assets originate strictly from official, publicly accessible product pages on [Merinos Official Website](https://www.merinos.com.tr/) and official CDN (`sm.mncdn.com`, `wwwmerinoscomtr.sm.mncdn.com`).
- **Host Allowlist Enforcement**: All image URL discovery, redirects, and binary downloads are restricted strictly to allowlisted official domains:
  - `merinos.com.tr`
  - `www.merinos.com.tr`
  - `sm.mncdn.com`
  - `wwwmerinoscomtr.sm.mncdn.com`
- **Rights Modes**:
  1. `URL_ONLY` (Default Mode): Extracts and validates image URL provenance metadata without downloading image binaries or creating database records.
  2. `AUTHORIZED_INTERNAL`: Explicit authorization mode (`--apply` required) to download, validate, sanitize, and ingest primary product images into `CarpetImageModel`.
- **Image Safety Controls**:
  - Max file size limit: 15 MB
  - Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`
  - Dimension constraints: Min 128x128px, Max 12000x12000px, Max 80M pixels
  - Image sanitization: EXIF orientation normalization & metadata stripping via Pillow/OpenCV decode pipeline.
  - Deduplication: Content SHA-256 hash tracking and atomic rollback on failure.
- **Readiness Transition**:
  - Before primary image activation: `NO_PRIMARY_IMAGE`
  - After primary image activation: `STYLE_DNA_MISSING`
- **False-Positive Catalog Cleanup Notice (A2A.1)**:
  - Discovered 6 non-product blog archive URLs (`/blog/month/YYYY-MM`) incorrectly parsed as SKUs (`2022 10`..`2024 11`) during initial seed ingestion.
  - All 6 invalid records safely deleted via `cleanup_merinos_catalog_false_positives.py`.
  - Parser URL & SKU validation hardened in `merinos_parser.py` to permanently reject blog/archive/nav routes.
  - Canonical Merinos catalog baseline reconciled to **232 real products** (227 with active primary image, 5 without).
- **Scope Boundary**: Style DNA batch analysis is NOT executed during A2 (reserved for Post-v1 A3).

---

## File Structure

- `merinos-catalog-source.json`: Raw acquisition provenance dataset containing SKUs, collection mappings, available sizes, and product page URLs.
- `merinos-catalog-curation.json`: Formatted import dataset adhering strictly to `carpet-catalog-curation-v1` schema.
- `activation-report.json`: Metadata acquisition summary report (A1).
- `merinos-image-source.json`: Image URL candidate discovery provenance dataset (A2).
- `merinos-image-activation.json`: Product image ingestion activation sidecar (A2).
- `image-activation-report.json`: Product image activation summary report (A2).

---

## Usage Commands

### 1. Default URL-Only Discovery (Safe, No DB Mutating Downloads)
```bash
python -m app.scripts.activate_merinos_catalog_images --rights-mode URL_ONLY
```

### 2. Authorized Internal Product Image Ingestion
```bash
python -m app.scripts.activate_merinos_catalog_images --rights-mode AUTHORIZED_INTERNAL --apply
```
