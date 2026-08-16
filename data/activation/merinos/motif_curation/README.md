# POST-v1 A5 — Carpet ↔ Motif / Story Curation (Explicit Product-Level Association Activation)

## Overview
This directory contains the review queue, human curation sidecar results, and explicit product-level motif and story curation dataset activated in **POST-v1 A5**.

All product associations adhere strictly to the `carpet-catalog-curation-v1` schema and existing GÖREV 11 domain models (`CarpetMotifAssociationModel`, `CarpetMotifAssociationSourceModel`, `CarpetStoryAssociationModel`).

## Core Invariants & Governance Rules
1. **Manual Presence Review**: Every `CURATOR_CONFIRMED` association corresponds to genuine human visual inspection of the product's primary image. No automated motif detection models (CLIP/CNN/YOLO/SAM), LLM image inference, OCR, or Style DNA heuristics were used.
2. **Strict Invariants**:
   - `CURATOR_CONFIRMED`: Requires non-empty `curation_note` detailing form-oriented visual evidence.
   - `SOURCE_DOCUMENTED`: Requires $\ge 1$ product-specific presence source.
   - `UNCERTAIN`: Requires non-empty `uncertainty_note` and MUST NEVER carry story associations.
   - `UNKNOWN` status claim (`claim-mystery-hook-unknown`): MUST NEVER attach to any carpet.
   - `CONTEXTUAL` & `CONTESTED` story claims: Require non-empty product-level `applicability_note`.
   - Story Claim Motif Match: A story association may only attach a claim belonging to the exact same motif as its parent motif association.
3. **Modern Product Safety**:
   - Associations represent curated visual linkages for narrative exploration ("Bu üründe küratöryel olarak tanımlanan görsel motif, kaynaklandırılmış bu anlatı temasını keşfetmek için bir bağlantı sunabilir").
   - Does NOT infer manufacturer intent, historical origin, ethnic identity, or religious purpose.
4. **Stale Review Protection**: Review sidecar records `primary_image_id` and `image_sha256`. If a product's primary image changes, `check_stale_reviews()` flags `STALE_IMAGE_REVIEW`.
5. **Immutability & Boundaries**:
   - Catalog Baseline: 232 products.
   - Primary Images: 227 images.
   - Style DNA: 224 COMPLETE, 3 PARTIAL, 5 NO_PRIMARY_IMAGE.
   - Motif Knowledge: 6 sources, 13 motifs, 12 claims.
   - HistoricalReference untouched.
   - 0 schema migrations.

## Summary of Activated Pilot Curation
- **Products Reviewed**: 10
- **Products Associated with Motifs**: 8
- **Products Associated with Stories**: 7
- **Motif Associations Total**: 12 (11 `CURATOR_CONFIRMED`, 1 `UNCERTAIN`, 0 `SOURCE_DOCUMENTED`)
- **Story Associations Total**: 11 (8 `DOCUMENTED`, 2 `CONTEXTUAL`, 1 `CONTESTED`, 0 `UNKNOWN`)
