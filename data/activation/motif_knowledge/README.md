# POST-v1 A4 — Real Source-Backed Motif Knowledge Activation

## Overview
This directory contains the curated motif story and source provenance dataset activated in **POST-v1 A4**.

All motif definitions, claim interpretations, and source linkages adhere strictly to the `motif-story-curation-v1` schema and the `motif-story-knowledge-v1` domain specification.

## Core Rules & Invariants
1. **Neutral Motif Identity**: `MotifModel` contains only form-oriented visual descriptions (e.g. geometric shape, symmetry, contour). It contains no symbolism or claim text.
2. **Strict Status Invariants**:
   - `DOCUMENTED`: $\ge 1$ source link, non-empty claim text directly supported by source.
   - `CONTEXTUAL`: $\ge 1$ source link, non-empty claim text, non-empty `context_note`.
   - `CONTESTED`: $\ge 2$ distinct source links, non-empty claim text, non-empty `contest_note`.
   - `UNKNOWN`: `claim_text_tr = null`, `theme_keys = []`, non-empty `uncertainty_note`.
3. **Canonical Narrative Themes**: Only exact frozen keys (`N1`..`N8`): `nature_growth`, `belonging_home`, `journey_discovery`, `continuity_connection`, `balance_order`, `renewal_transformation`, `tradition_craft`, `cultural_heritage`.
4. **Boundary Isolation**:
   - No `CarpetMotifAssociation` or `CarpetStoryAssociation` created in A4 (reserved for A5).
   - No `HistoricalReferenceMetadata` altered in A4 (reserved for A6/A7).
   - Catalog Baseline unchanged: 232 products, 227 primary images, 227 style profiles.

## Summary of Activated Data
- **Curated Sources**: 6 (Metropolitan Museum of Art, Victoria and Albert Museum, Kurt Erdmann, Walter B. Denny, Atatürk Kültür Merkezi)
- **Neutral Motifs**: 13 (`medallion`, `mihrab`, `palmette`, `lotus`, `rosette`, `cloud-band`, `scrolling-vine`, `geometric-star`, `ram-horn`, `tree-of-life`, `elibelinde`, `comb`, `mystery-hook`)
- **Motif Story Claims**: 12 (7 DOCUMENTED, 2 CONTEXTUAL, 2 CONTESTED, 1 UNKNOWN)
- **Claim Source Links**: 19
- **Claim Narrative Theme Links**: 21
