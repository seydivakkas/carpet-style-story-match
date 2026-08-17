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
