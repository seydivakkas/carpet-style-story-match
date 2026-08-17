# V2-05 — Cultural Claim Validator & Source-Bound Story Curator Architecture

## Overview

The V2-05 module implements the **Cultural Claim Validation Engine** (`cultural-claim-v1.0.0`, `cultural-claim-validator-v1.0.0`) and **Source-Bound Story Curator** (`source-bound-story-v1.0.0`, `story-grounding-policy-v1.0.0`) for the Carpet Style & Story Match project.

It operates strictly downstream of **EvidencePack** (`evidence-pack-v1.0.0` from V2-04), enforcing strict safety and provenance invariants:
1. *"What may we safely say based on the retrieved evidence?"* (`ValidatedCulturalClaim` in categorical statuses `DOCUMENTED`, `CONTEXTUAL`, `CONTESTED`, `UNKNOWN`).
2. *"How may we present that validated information naturally to the user without inventing additional cultural meaning?"* (`StoryPresentation` in `TEMPLATE_ONLY` default mode).

---

## 1. Pipeline Position & Boundaries

```
PIXEL
 ↓
VISUAL OBSERVATION (Style DNA & CIELAB K-Means)
 ↓
MOTIF CANDIDATE
 ↓
VERIFICATION (Curator Confirmed / Verified Canonical)
 ↓
SOURCE RESEARCH (V2-04 Evidence RAG Engine)
 ↓
EVIDENCE PACK (evidence-pack-v1.0.0)
 ↓
CULTURAL CLAIM VALIDATOR (V2-05)
 ↓
SOURCE-BOUND STORY PRESENTATION (V2-05)
 ↓
USER PRESENTATION
```

V2-05 begins strictly at **EvidencePack**. It does NOT re-run image analysis, VLM motif detection, color clustering, motif verification, or web research.

---

## 2. Frozen Invariants & Safety Rules

- **Input Isolation**: Claim validation and story presentation receive ONLY `EvidencePack` or `ValidatedCulturalClaim` objects. NO image input, NO pixel-to-story shortcut, NO VLM memory reuse.
- **Categorical Claim Statuses**: Exactly `DOCUMENTED`, `CONTEXTUAL`, `CONTESTED`, `UNKNOWN`. Numeric truth scores (`truth_score`, `confidence`, `historical_probability`) are **STRICTLY FORBIDDEN**.
- **Tier 1 ≠ Automatic DOCUMENTED**: A Tier-1 primary institutional source must directly support the claim content to achieve `DOCUMENTED`.
- **Preservation of Uncertainty & Discrepancy**:
  - `CONTEXTUAL`: Context bounds (region, period, tradition, institution) MUST be preserved in claim scope and presentation text.
  - `CONTESTED`: Conflicting evidence sides MUST be retained without selecting an automatic winner.
  - `UNKNOWN`: Insufficient evidence MUST be explicitly disclosed. It CANNOT be decorated into speculative "probably" statements.
- **Grounding Integrity**:
  - Every story section text MUST trace to `>= 1 validated claim_id`.
  - Every `StoryCitation` MUST resolve to an existing `EvidenceUnit` and `ResearchSourceDocument` in the `EvidencePack`.
  - NO origin authentication statements ("Seljuk carpet confirmed", "Safavid carpet confirmed").
  - NO color symbolism or dye material inferences from visual pixels alone (`VISIBLE COLOR != DYE MATERIAL`, `COLOR != CULTURAL MEANING`).
- **Database & Data Isolation**: Validated claims are returned as structured API DTOs and are **NOT** automatically written into the production `ClaimModel` database table. `MIGRATION: NONE`.

---

## 3. Claim Validation Architecture (`cultural-claim-v1.0.0`)

### Status Definitions & Rules
| Status | Definition | Rules |
| :--- | :--- | :--- |
| **`DOCUMENTED`** | Directly supported by qualifying evidence without contradiction. | `>= 1` qualifying `SUPPORTS` link, non-empty locator, `0` contradictions. |
| **`CONTEXTUAL`** | Supported only within explicit narrow scope context. | Scope bounds (region, period, tradition, object) MUST be recorded in `ClaimScope`. |
| **`CONTESTED`** | Qualifying evidence contains conflicting interpretations. | Both `SUPPORTS` and `CONTRADICTS` links retained without auto-resolving winners. |
| **`UNKNOWN`** | Insufficient qualifying evidence in EvidencePack. | Assigned when no qualifying support exists. Discloses evidence insufficiency. |

---

## 4. Source-Bound Story Presentation (`source-bound-story-v1.0.0`)

### Presentation Provider Modes
- **`TEMPLATE_ONLY` (Default & Canonical Baseline)**: Deterministic Turkish template rendering. Operates 100% offline without GPU, cloud API keys, or external network.
- **`LOCAL_OPENAI_COMPATIBLE`**: Generic configuration-driven adapter (`NOT_CONFIGURED` by default).
- **`REMOTE_OPENAI_COMPATIBLE`**: Generic configuration-driven adapter (`NOT_CONFIGURED` by default).

### Story Grounding Auditor (`story-grounding-policy-v1.0.0`)
- Validates section claim references (`claim_ids`), citation resolution (`citation_ids`), status preservation, and forbids unsourced statements or external citations.

---

## 5. API Endpoints

- `POST /api/v1/research/validate-claims`: Validates cultural claims against an input `EvidencePack`.
- `POST /api/v1/research/story`: Generates a `StoryPresentation` strictly bound to validated claims.
- `POST /api/v1/research/narrative`: Composed pipeline (`EvidencePack` -> `ValidatedCulturalClaim[]` -> `StoryPresentation`).
- `GET /api/v1/research/provider-status`: Exposes provider status and active policy versions.
