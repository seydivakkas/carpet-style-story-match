# POST-v1 A4 / A4A — Real Source-Backed Motif Knowledge Activation & Provenance Reconciliation

## Overview
This directory contains the curated motif story and source provenance dataset activated in **POST-v1 A4** and reconciled in **POST-v1 A4A**.

All motif definitions, claim interpretations, and source linkages adhere strictly to the `motif-story-curation-v1` schema and the `motif-story-knowledge-v1` domain specification.

## Core Rules & Invariants
1. **Neutral Motif Identity**: `MotifModel` contains only form-oriented visual descriptions (e.g. geometric shape, symmetry, contour). It contains no symbolism or claim text.
2. **Strict Status Invariants**:
   - `DOCUMENTED`: $\ge 1$ source link, non-empty claim text directly supported by source.
   - `CONTEXTUAL`: $\ge 1$ source link, non-empty claim text, non-empty `context_note`.
   - `CONTESTED`: $\ge 2$ distinct source links, non-empty claim text, non-empty `contest_note`.
   - `UNKNOWN`: `claim_text_tr = null`, `theme_keys = []`, non-empty `uncertainty_note`.
3. **Unambiguous Source Identity**:
   - `MUSEUM_OBJECT` records (e.g. Accession 14.40.714) are strictly separated from `MUSEUM_CATALOG` / `ACADEMIC_BOOK` publications (e.g. Charles Grant Ellis 1988 catalog).
   - Every positive claim must feature a non-empty `locator` (page number, page range, accession ID) and a concise paraphrase `source_note`.
4. **Canonical Narrative Themes**: Only exact frozen keys (`N1`..`N8`): `nature_growth`, `belonging_home`, `journey_discovery`, `continuity_connection`, `balance_order`, `renewal_transformation`, `tradition_craft`, `cultural_heritage`.
5. **Boundary Isolation**:
   - No `CarpetMotifAssociation` or `CarpetStoryAssociation` created (reserved for A5).
   - No `HistoricalReferenceMetadata` altered (reserved for A6/A7).
   - Catalog Baseline unchanged: 232 products, 227 primary images, 227 style profiles.

## Summary of Reconciled Inventory (A4A)
- **Curated Sources**: 6
  1. `met-museum-oriental-rug-catalog-1988` (MUSEUM_CATALOG — Charles Grant Ellis 1988)
  2. `denny-how-to-read-islamic-carpets-2014` (ACADEMIC_BOOK — Walter B. Denny 2014)
  3. `erdmann-seven-hundred-years-1970` (ACADEMIC_BOOK — Kurt Erdmann 1970)
  4. `va-museum-carpet-collection-1931` (MUSEUM_CATALOG — C. E. C. Tattersall 1931)
  5. `akm-anatolian-motifs-ethnography-1995` (INSTITUTIONAL_PUBLICATION — Güran Erbek 1995)
  6. `met-museum-safavid-medallion-carpet-14104` (MUSEUM_OBJECT — Accession 14.40.714)
- **Neutral Motifs**: 13 (`medallion`, `mihrab`, `palmette`, `lotus`, `rosette`, `cloud-band`, `scrolling-vine`, `geometric-star`, `ram-horn`, `tree-of-life`, `elibelinde`, `comb`, `mystery-hook`)
- **Motif Story Claims**: 12 (6 DOCUMENTED, 3 CONTEXTUAL, 2 CONTESTED, 1 UNKNOWN)
  - `claim-lotus-rebirth` downgraded from DOCUMENTED to CONTEXTUAL to avoid unbacked universalized symbolism.
- **Claim Source Links**: 20
- **Claim Narrative Theme Links**: 21
