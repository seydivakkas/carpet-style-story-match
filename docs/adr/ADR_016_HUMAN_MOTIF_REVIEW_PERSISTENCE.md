# ADR 016 — Human Motif Review Persistence Foundation

- **Status**: Approved
- **Date**: 2026-08-17
- **Authors**: AI & Data Systems Team
- **Context**: V2-06 Human Motif Review Workflow

## Context and Problem Statement

AI motif candidate detection (V2-02 / V2-03) produces unverified visual motif candidates (`AI_CANDIDATE`). To prevent AI hallucinations or unverified visual mappings from contaminating downstream academic research (V2-04) or cultural stories (V2-05), human curator verification is required.

Previously, `CarpetMotifAssociation` existed for curated catalog product knowledge (`carpets.id`). Reusing `CarpetMotifAssociation` for transient user upload candidates would violate domain separation between catalog curation and user upload review. Furthermore, no table existed to persist review subjects, immutable candidate snapshots, review event audit trails, optimistic concurrency tokens, or idempotency keys.

## Decision Drivers

1. **Audit Integrity**: Review history must be append-only and survive API restarts, browser refreshes, or worker restarts.
2. **Domain Separation**: Catalog product curation (`CarpetMotifAssociation`) must remain separate from user upload AI candidate review.
3. **Concurrency & Idempotency**: Prevent silent lost updates under concurrent review and support safe HTTP request retries.
4. **No Cascade Deletion**: FK constraints must use `RESTRICT` to prevent accidental loss of governance audit events.
5. **No Automatic Downstream Execution**: Review decisions must not trigger network research, claims, or stories automatically.

## Considered Options

1. **Option 1**: Reuse `CarpetMotifAssociation` table for user uploads. (Rejected: Violates domain separation and lacks candidate snapshot/audit fields).
2. **Option 2**: Store review decisions in transient memory / cache. (Rejected: Fails durability across restarts).
3. **Option 3**: Dedicated ORM persistence models (`motif_review_subjects` and `motif_review_events`) with Alembic migration `016`. (Selected).

## Decision Outcome

Option 3 was selected. Alembic migration `2026_08_17_016_create_motif_review_persistence.py` introduces:
- `motif_review_subjects`: Immutable candidate identity, canonical snapshot JSON, SHA-256 hash, and optimistic concurrency version token (`review_version`).
- `motif_review_events`: Append-only audit trail with server-owned resulting status mapping (`CONFIRM` -> `CURATOR_CONFIRMED`, `UNCERTAIN` -> `UNCERTAIN`, `REJECT` -> `REJECTED`), snapshot hash verification, idempotency key, and `ondelete="RESTRICT"` FKs.

## Consequences

- **Positive**: Complete audit trail transparency, concurrency protection, idempotency support, and strict data isolation.
- **Negative**: Additional database table management and schema migration.

## Addendum V2-06A.1 — Reviewer Trust Boundary Hardening & Atomic Concurrency

- **Status**: Approved (2026-08-17)
- **Decision**: 
  1. Alembic migration `2026_08_17_017` removes `server_default='GATEWAY_TRUSTED'` from `motif_review_events.reviewer_boundary`. All default trust provenance assignments are removed across ORM models, Pydantic DTOs, and domain services. Missing trust boundary fails closed.
  2. Optimistic concurrency in `MotifReviewRepository.append_review_event` is upgraded to use an atomic SQL compare-and-update primitive (`UPDATE motif_review_subjects SET review_version = review_version + 1 WHERE id = :id AND review_version = :expected_version`) to guarantee race-free version reservation under concurrent writers.

