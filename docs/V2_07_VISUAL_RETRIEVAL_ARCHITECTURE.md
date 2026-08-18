# V2-07 — Historical + Catalog Visual Retrieval Architecture

## Overview

V2-07 introduces two independent, deterministic 9D Style DNA visual retrieval engines:
1. `CATALOG_VISUAL_RETRIEVAL`: Retrieves visually similar current catalog carpets from the eligible production catalog corpus.
2. `HISTORICAL_VISUAL_RETRIEVAL`: Retrieves visually similar verified historical reference objects from the eligible museum reference corpus.

Both engines operate purely on **Visual Proximity** derived from the 9-dimensional Style DNA representation (`style-dna-v1.0.0`).

---

## Safety Invariants & Non-Inferences

To preserve scientific rigor and prevent AI hallucination or false cultural claims, the following strict invariants are enforced:

- **VISUAL RETRIEVAL != AUTHENTICATION**
- **VISUAL RETRIEVAL != ORIGIN CLASSIFICATION**
- **VISUAL RETRIEVAL != PERIOD CLASSIFICATION**
- **VISUAL RETRIEVAL != CULTURAL IDENTITY**
- **VISUAL RETRIEVAL != BRAND CLASSIFICATION**
- **VISUAL PROXIMITY SCORE != CONFIDENCE**
- **VISUAL PROXIMITY SCORE != PROBABILITY**
- **HISTORICAL MATCH != HISTORICAL ORIGIN**
- **CATALOG MATCH != PRODUCT RECOMMENDATION / ADVICE**
- **MUSEUM METADATA != MODEL PREDICTION**

A high visual proximity score indicates mathematical similarity in color, contrast, visual complexity, structural order, rhythm, focal strength, and form language — **not** identical weaver origin, historical era, or brand lineage.

---

## Architecture Diagram

```
Query Carpet / Vector
          │
          ▼
   style-dna-v1.0.0 (9D)
          │
    ┌─────┴───────────────────────────┐
    │                                 │
    ▼                                 ▼
Catalog Corpus                   Historical Corpus
(224 COMPLETE)                   (45 COMPLETE)
    │                                 │
    ▼                                 ▼
CATALOG_VISUAL_RETRIEVAL         HISTORICAL_VISUAL_RETRIEVAL
    │                                 │
    ▼                                 ▼
CatalogVisualMatch[]             HistoricalVisualMatch[]
```

The two corpora are ranked **independently**. Results are **never merged** into a single global list.

---

## 9D Canonical Dimension Order & Weight Policy

1. `D1 color_energy` (1.0)
2. `D2 color_diversity` (1.0)
3. `D3 contrast` (1.0)
4. `D4 warmth` (1.0)
5. `D5 visual_complexity` (1.0)
6. `D6 structural_order` (1.0)
7. `D7 rhythm_repetition` (1.0)
8. `D8 focal_strength` (1.0)
9. `D9 form_language` (1.0)

*Note: Structural Order (`D6`) and Rhythm Repetition (`D7`) remain strictly separate dimensions. All 9 dimensions use uniform frozen weights $w_i = 1.0$. No user preference or importance weighting is applied during visual retrieval.*

---

## Distance & Proximity Score Mathematics

For normalized 9D query vector $q$ and candidate vector $c$ ($q_i, c_i \in [0.0, 1.0]$):

$$d_{\text{norm}}(q, c) = \sqrt{\frac{\sum_{i=1}^9 w_i (q_i - c_i)^2}{\sum_{i=1}^9 w_i}}$$

With equal weights $w_i = 1.0$ for all 9 dimensions, $\sum w_i = 9.0$.

Since $(q_i - c_i)^2 \in [0.0, 1.0]$, the normalized distance $d_{\text{norm}}$ is bounded strictly by:

$$0.0 \le d_{\text{norm}} \le 1.0$$

*(Note: Prior turn response text mentioned $\sqrt{2}$, which was an informal summary typo; the actual codebase implementation in `distance.py` computes normalized distance $d_{\text{norm}} \in [0.0, 1.0]$).*

The visual proximity score is computed from the unrounded normalized distance:

$$\text{visual\_proximity\_score} = \text{round}\left(\text{max}\left(0.0, \text{min}\left(100.0, 100.0 \times (1.0 - d_{\text{norm}})\right)\right), 2\right)$$

- Identical 9D vectors ($d_{\text{norm}} = 0.0$) $\rightarrow$ score **100.00**.
- Midpoint distance ($d_{\text{norm}} = 0.5$) $\rightarrow$ score **50.00**.
- Opposite extreme 9D vectors ($d_{\text{norm}} = 1.0$) $\rightarrow$ score **0.00**.

Candidates are sorted primarily by ascending unrounded $d_{\text{norm}}$ prior to score presentation rounding, preventing artificial tie collapse.

---

## Deterministic Tie-Breaking & Corpus Fingerprints

- **Tie-Breaking**: When two candidates yield identical distances, secondary sorting orders deterministically by stable identifiers:
  - Catalog: `sku ASC, catalog_id ASC`
  - Historical: `reference_key ASC, historical_reference_id ASC`
- **Corpus Fingerprint**: A SHA-256 hash is computed over all eligible candidates in canonical order `(id, sorted 9D vector)`. Reordering database rows does not alter the hash, while mutating any eligible candidate's 9D vector immediately changes the hash.

---

## Corpus Eligibility & Provenance Accounting

### Catalog Corpus
- Total catalog products in DB: **232**
- Eligible for retrieval (`COMPLETE` status + primary image): **224**
- Excluded `PARTIAL` Style DNA: **3**
- Excluded missing primary image: **5**
- Excluded test fixtures (`DN-1001`): **Excluded from catalog DB query**
- Total: $224 + 3 + 5 = 232$

### Historical Corpus Provenance
- Total historical references in DB: **100**
- Eligible for retrieval (`COMPLETE` status + primary image): **45**
- Rights / Access Ineligible (Non-Open Access / Rights Review Required): **55**
- Genuinely missing image (Open Access but no file): **0**
- Missing Style DNA: **0**
- Incompatible version: **0**
- Total: $45 + 55 = 100$

---

## API Endpoints

- `POST /api/v1/visual-retrieval`: Returns both catalog and historical visual matches.
- `POST /api/v1/visual-retrieval/catalog`: Catalog visual matches only.
- `POST /api/v1/visual-retrieval/historical`: Historical visual matches only.
