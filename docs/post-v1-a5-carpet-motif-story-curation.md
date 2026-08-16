# POST-v1 A5 — Carpet ↔ Motif / Story Curation Summary

## Overview
POST-v1 A5 activated explicit, product-level curated associations linking catalog carpets to neutral motifs (`CarpetMotifAssociationModel`) and applicable story claims (`CarpetStoryAssociationModel`).

## Pilot Cohort Curation Summary Table

| SKU | Collection | Motif Key | Evidence Type | Story Claim Key | Claim Status | Curation / Applicability Notes |
|-----|------------|-----------|---------------|-----------------|--------------|--------------------------------|
| `73941 060` | Elegance | `medallion` | `CURATOR_CONFIRMED` | `claim-medallion-central-focus` | `DOCUMENTED` | Large central circular medallion with pendents confirmed on primary image. |
| `73941 060` | Elegance | `scrolling-vine` | `CURATOR_CONFIRMED` | `claim-scrolling-vine-continuous-growth` | `DOCUMENTED` | Continuous scrolling arabesque vines on border field. |
| `72484 062` | Arden | `geometric-star` | `UNCERTAIN` | None (`[]`) | N/A | Concentric rectangular framing observed; star motif identity uncertain. 0 stories attached. |
| `73928 060` | Vega | `geometric-star` | `CURATOR_CONFIRMED` | `claim-geometric-star-spatial-order` | `DOCUMENTED` | Contemporary modular geometric block layout confirmed. |
| `73338 060` | Ritim | `geometric-star` | `CURATOR_CONFIRMED` | `claim-geometric-star-spatial-order` | `DOCUMENTED` | Intersecting diagonal lattice network confirmed. |
| `69799 060` | Premium | `palmette` | `CURATOR_CONFIRMED` | `claim-palmette-floral-composition` | `DOCUMENTED` | Stylized palmettes throughout field confirmed. |
| `69799 060` | Premium | `scrolling-vine` | `CURATOR_CONFIRMED` | `claim-scrolling-vine-continuous-growth` | `DOCUMENTED` | Circular rumî branches linking palmette motifs confirmed. |
| `54094 260` | Launge | `geometric-star` | `CURATOR_CONFIRMED` | `claim-geometric-star-spatial-order` | `DOCUMENTED` | Repeating elongated geometric lattice network confirmed. |
| `91001 020` | Valeria | `tree-of-life` | `CURATOR_CONFIRMED` | `claim-tree-of-life-anatolian-context` | `CONTEXTUAL` | Vertically aligned cypress/tree forms on terracotta field confirmed. |
| `91001 020` | Valeria | `comb` | `CURATOR_CONFIRMED` | `claim-comb-cleanliness-vs-weave-tool` | `CONTESTED` | Toothed comb-like geometric formations confirmed; contested status preserved. |
| `19770 071` | Rodin | `medallion` | `CURATOR_CONFIRMED` | `claim-medallion-central-focus` | `DOCUMENTED` | Central almond/oval medallion confirmed. |
| `19770 071` | Rodin | `lotus` | `CURATOR_CONFIRMED` | `claim-lotus-rebirth` | `CONTEXTUAL` | Stylized lotus contours around medallion border confirmed. |

## Invariant Verification Results
- **UNCERTAIN motif story invariant**: PASS (0 stories attached to UNCERTAIN motif on `72484 062`).
- **UNKNOWN claim invariant**: PASS (0 carpet story associations for `claim-mystery-hook-unknown`).
- **Contextual / Contested applicability notes**: PASS (All 3 CONTEXTUAL/CONTESTED story links have explicit applicability notes).
- **Parent Motif Claim Match**: PASS (All 11 story links match parent motif ID).
- **Impotency & Dry-run**: PASS (Second import run created 0 new records).
