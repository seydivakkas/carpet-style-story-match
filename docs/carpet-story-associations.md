# Carpet Story Associations v1 Spec

## Architecture & Separation of Concerns

Carpet Story Associations strictly separate visual motif presence on a carpet from the cultural/story claims associated with that motif.

```text
+-------------------+       +-------------------------------+       +------------------+
|   CarpetModel     |-----> | CarpetMotifAssociationModel   |-----> |   MotifModel     |
+-------------------+       +-------------------------------+       +------------------+
                                           |
                                           v
                            +-------------------------------+       +------------------+
                            | CarpetStoryAssociationModel   |-----> |MotifStoryClaim   |
                            +-------------------------------+       +------------------+
```

---

## Technical & Curation Invariants

1. **Two-Layer Association Model**:
   - `CarpetMotifAssociationModel`: Links `carpet_id` $\leftrightarrow$ `motif_id`. Represents physical visual presence.
   - `CarpetStoryAssociationModel`: Links `carpet_motif_association_id` $\leftrightarrow$ `claim_id`. Represents explicit story claim application.

2. **No Auto-Inheritance**:
   - Associating a motif with a carpet DOES NOT automatically attach all story claims of that motif!
   - Every story claim association MUST be explicitly declared in the curation dataset.

3. **Motif Presence Invariants**:
   - `CURATOR_CONFIRMED`: `curation_note` required.
   - `SOURCE_DOCUMENTED`: $\ge 1$ presence source (`CarpetMotifAssociationSourceModel`) required.
   - `UNCERTAIN`: `uncertainty_note` required. CANNOT have any story claim associations!

4. **Story Claim Applicability Rules**:
   - `DOCUMENTED` claim: Explicit association valid.
   - `CONTEXTUAL` claim: `applicability_note` required (e.g. region, period, context).
   - `CONTESTED` claim: `applicability_note` required. Preserves `status = CONTESTED`.
   - `UNKNOWN` claim: CANNOT be attached to a carpet (`CARPET_STORY_UNKNOWN_CLAIM_NOT_APPLICABLE`).
   - Claim motif mismatch (`claim.motif_id != association.motif_id`) raises `CARPET_STORY_MOTIF_MISMATCH`.

5. **Two-Layer Source Separation**:
   - API responses strictly separate `presence_sources` (where/how motif presence was documented) from `claim_sources` (literature sources backing claim meaning).
