# Motif Story Knowledge v1 Specification

## Purpose
The Motif Story Knowledge layer models human-curated, source-provenanced carpet motif definitions and story claims without any automated inferences or AI hallucinated stories.

```
Curated Source + Neutral Motif Identity -> Motif Story Claim -> Source Links + Optional Narrative Theme Links
```

## Core Principles
1. **Motif Identity != Motif Story**: A motif (`MotifModel`) records neutral visual descriptions only. It contains no `meaning`, `story`, `symbolism`, or `narrative_theme` columns.
2. **Absence of Claim != UNKNOWN**: 0 claims on a motif means no curated story data exists. An `UNKNOWN` claim indicates curation was performed, but no verified narrative interpretation could be established in sources.
3. **No Automatic Motif Recognition**: No SAM, CNN, CLIP, or image similarity classification is used to assign motifs to carpets.
4. **No Carpet -> Motif Auto Link**: Carpets are not automatically linked to motifs.
5. **No Source Quality Score**: Provenance is categorical and explainable. No fake precision (e.g., `trust_score = 0.92`).
6. **No User Psychology**: Motif stories do not infer user personality or psychological traits.

## Story Statuses
- `DOCUMENTED`: Supported directly by $\ge 1$ curated source. Requires `claim_text_tr`.
- `CONTEXTUAL`: Supported in specific regions, periods, or traditions. Requires `claim_text_tr`, `context_note`, and $\ge 1$ source.
- `CONTESTED`: Multiple distinct interpretations exist in sources. Requires `claim_text_tr`, `contest_note`, and $\ge 2$ distinct sources.
- `UNKNOWN`: Verified uncertainty. `claim_text_tr` MUST BE null, and 0 theme links allowed.

## Curation Import & Safety
- **Schema Version**: `motif-story-curation-v1`
- Implemented in `MotifKnowledgeImporter` with atomic transactions and `--dry-run` validation support.
- Idempotent: Importing identical datasets creates no duplicate records. Conflicting stable keys raise `CurationConflictError`.
- **Public API**: Read-only endpoints (`GET /motifs`, `GET /motif-story-claims`, `GET /sources`). Curation writes are internal.
