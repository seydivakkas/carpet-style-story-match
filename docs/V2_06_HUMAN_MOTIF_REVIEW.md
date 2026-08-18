# V2-06 — Human Motif Review Architecture & Persistence Foundation

## Overview

V2-06 establishes the human governance decision boundary between AI-detected visual motif candidates and verified research-eligible canonical motifs.

```
AI Motif Candidate (AI_CANDIDATE)
          │
          ▼
   Human Review Queue
          │
   Curator Decision
    ├── CONFIRM   ──► CURATOR_CONFIRMED (SOURCE_RESEARCH_ALLOWED)
    ├── UNCERTAIN ──► UNCERTAIN         (SOURCE_RESEARCH_BLOCKED)
    └── REJECT    ──► REJECTED          (SOURCE_RESEARCH_BLOCKED)
          │
          ▼
Append-Only Audit Event Log (motif_review_events)
```

## Governance Principles

1. **AI Candidate ≠ Curator Confirmed**: High model confidence (e.g. 0.999) does NOT auto-confirm a candidate. Confirmation requires an explicit curator review event.
2. **Review Decision ≠ Cultural Claim**: A visual confirmation asserts only that the image evidence matches the canonical motif mapping. It does NOT assert origin, dynasty, period, or symbolism.
3. **No Automatic Downstream Side Effects**: Submitting a review decision does NOT trigger automated network research, cultural claim validation, or story generation. It only sets the `research_eligibility` state.
4. **Append-Only History**: Prior review decisions are never mutated or deleted. Re-reviews generate new sequential events with a `supersedes_review_id` reference.
5. **RESTRICT Foreign Keys**: Database foreign keys use `ondelete="RESTRICT"` to prevent cascade deletion of audit history.

## Durable Persistence Schema

- **`motif_review_subjects`**: Stores the immutable identity and canonical JSON candidate snapshot hash (`SHA-256`), with optimistic concurrency token `review_version`. Unique constraint on `(analysis_id, candidate_id)`.
- **`motif_review_events`**: Stores append-only curator review decisions (`CONFIRM`, `UNCERTAIN`, `REJECT`), mapped resulting statuses (`CURATOR_CONFIRMED`, `UNCERTAIN`, `REJECTED`), reason codes, notes, reviewer reference, reviewer boundary, snapshot hash verification, idempotency key, and sequential version number. Unique constraints on `(review_subject_id, idempotency_key)` and `(review_subject_id, version)`.

## Snapshot Hashing & Concurrency

Candidate snapshots are serialized to canonical UTF-8 JSON with sorted keys before SHA-256 hashing. Volatile request metadata (timestamps, HTTP headers, reviewer identity) is excluded. During review submission, optimistic concurrency is verified (`expected_version == subject.review_version`), and snapshot hashes are verified to prevent stale candidate reviews.

## Reviewer Trust Provenance & Atomic Concurrency (V2-06A.1 Hardening)

1. **Reviewer Boundary Fail-Closed**:
   - `reviewer_ref` is audit provenance (who submitted the review), NOT authentication.
   - `reviewer_boundary` is trust provenance (`GATEWAY_TRUSTED`, `DEVELOPMENT_ADMIN`, `SYSTEM_IMPORT`), NOT user authentication.
   - Database columns, Pydantic DTOs, and domain services have NO default values for `reviewer_boundary`. Missing trust boundary fails immediately. No boundary is inferred or defaulted to `GATEWAY_TRUSTED` when absent.
   - `GATEWAY_TRUSTED` may only be injected by verified server-side gateway context. Future client APIs cannot directly specify trusted boundaries.
2. **Atomic Optimistic Concurrency**:
   - Concurrency reservation uses an atomic SQL compare-and-update (`UPDATE motif_review_subjects SET review_version = review_version + 1 WHERE id = :id AND review_version = :expected_version`).
   - If `affected_rows == 0`, a `ReviewConcurrencyException` is raised.
   - Event insertion occurs within the same database transaction; any failure triggers transaction rollback, preserving `review_version`.

## Review API Security Boundary & Curator UI (V2-06B / V2-06B.1 Hardening)

1. **Access Modes**:
   - `DISABLED`: Default mode. Rejects all `/api/v1/reviews/motif-candidates` requests with HTTP 403 `REVIEW_ACCESS_DISABLED`.
   - `DEVELOPMENT_ADMIN`: Enabled in non-production environments (`APP_ENV != production`). Requires explicit non-empty `MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF` server configuration (no fallback default). Rejects if `MOTIF_REVIEW_DEVELOPMENT_REVIEWER_REF` is missing or in `APP_ENV=production`.
   - `GATEWAY_TRUSTED`: Requires a verified server-side gateway context on `request.state`. Arbitrary client headers (`X-Reviewer-Ref`, `X-User`, `X-Curator`, `X-Forwarded-User`) do NOT satisfy this mode and are rejected with HTTP 403 `REVIEW_ACCESS_DISABLED`.
2. **Client Request Body Boundaries**:
   - `MotifReviewDecisionClientBody` has `extra="forbid"`. Client requests containing `reviewer_ref`, `reviewer_boundary`, or `resulting_status` in HTTP bodies or query parameters are rejected with HTTP 422 `UNPROCESSABLE_ENTITY`.
3. **Safe Image Resolution**:
   - Image assets are resolved strictly via server-owned `image_asset_id` against `./data/uploads`.
   - Path traversal attempts (`../`, absolute paths) are neutralized via `Path(image_asset_id).name` and `target_path.is_relative_to(upload_root)` checks.
4. **Curator UI (`/reviews/motifs`)**:
   - Displays required disclaimer banner: *"Bu işlem motifin görsel eşleşmesini doğrular; kültürel anlam, köken, dönem veya özgünlük doğrulaması yapmaz."*
   - Displays `Geliştirme inceleme modu` badge in `DEVELOPMENT_ADMIN` mode.
   - Handles `REVIEW_ACCESS_DISABLED` with a controlled access-disabled notice.
