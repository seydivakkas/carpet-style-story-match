# Importance Profile Specification (v1)

## 1. Overview & Purpose

The **Importance Profile** captures explicit user declarations regarding which 9D carpet style dimensions ($D_1 \dots D_9$) are critical priorities, flexible trade-offs, or standard preferences during style matching.

It attaches to a reviewed `UserPreferenceProfile` (status `PROFILE_REVIEWED`) and transitions the assessment status to `IMPORTANCE_COMPLETE`.

---

## 2. Frozen Semantic Separation

Importance is strictly derived **ONLY** from **EXPLICIT USER SELECTION**. Zero system inference or heuristic estimation!

1. **Preference $\ne$ Importance**: Preference magnitude ($0.0 \dots 1.0$) measures aesthetic direction. Importance ($0.25 \dots 1.00$) measures priority weighting. A dimension with preference $0.90$ can be `FLEXIBLE`, while a dimension with preference $0.55$ can be `PRIORITY`.
2. **Confidence $\ne$ Importance**: Confidence measures evidence quality. Importance measures user priority. A low-confidence dimension ($0.15$) selected as `PRIORITY` retains weight $1.00$ without confidence multiplication or penalty.
3. **Response Strength $\ne$ Importance**: Strongly choosing an option in text/visual cards does NOT automatically imply priority.
4. **User Override $\ne$ Importance**: Overriding a preference value does NOT alter its importance level.
5. **No Personality Inference**: Importance selections reflect design preference priorities, not psychological traits.

---

## 3. Canonical Levels & Server-Owned Fixed Weights

- `IMPORTANCE_PROFILE_VERSION`: `importance-v1`

| Level | Server Fixed Weight | Selection Constraint | Default Behavior |
|---|---|---|---|
| `PRIORITY` | `1.00` | Max 3 dimensions | Explicitly selected by user |
| `STANDARD` | `0.60` | Unrestricted | Assigned to all unselected dimensions |
| `FLEXIBLE` | `0.25` | Max 3 dimensions | Explicitly selected by user |

- **No Zero Weight**: MVP v1 has no weight $= 0.0$. Minimum weight is `FLEXIBLE` ($0.25$).
- **Server-Owned Weights**: Client supplies level arrays (`priority_dimensions`, `flexible_dimensions`), server maps weights. Client cannot supply numeric weights (`extra = "forbid"`).

---

## 4. Selection Rules & Validation Invariants

1. **Maximum Priority**: $\le 3$ dimensions.
2. **Maximum Flexible**: $\le 3$ dimensions.
3. **Overlap Forbidden**: Dimension cannot be both `PRIORITY` and `FLEXIBLE` (`422 IMPORTANCE_SELECTION_OVERLAP`).
4. **Duplicates Forbidden**: Duplicate dimension keys in input arrays are rejected (`422 IMPORTANCE_SELECTION_DUPLICATE`).
5. **Unknown Dimension Forbidden**: Keys outside canonical $D_1 \dots D_9$ are rejected (`422 IMPORTANCE_SELECTION_UNKNOWN_DIMENSION`).
6. **Skip Semantics**:
   - `skip = true` requires `priority_dimensions = []` and `flexible_dimensions = []`.
   - Results in all 9 dimensions as `STANDARD` ($0.60$), with `completion_mode = SKIPPED_ALL_STANDARD`.
7. **Explicit Empty Selection**: `skip = false` with both selection lists empty is rejected (`422 IMPORTANCE_SELECTION_EMPTY`).

---

## 5. Completion Modes & Provenance

- `EXPLICIT_SELECTION`: User explicitly picked priority and/or flexible dimensions.
- `SKIPPED_ALL_STANDARD`: User explicitly chose to skip custom importance weighting.
- **No `INFERRED` mode**: Importance is never system-inferred.

---

## 6. Precondition & Immutability

- Creation requires `assessment.status == PROFILE_REVIEWED` and `user_preference_profile.status == REVIEWED` (`409 IMPORTANCE_REQUIRES_REVIEWED_PREFERENCE_PROFILE`).
- Once created, assessment status becomes `IMPORTANCE_COMPLETE`.
- ImportanceProfile is **immutable**. Posting a different selection returns `409 IMPORTANCE_PROFILE_ALREADY_EXISTS`. Posting the identical selection returns the existing profile (Idempotent call).

---

## 7. Known Limitations

- **No Weight 0 / Ignore**: Minimum weight is `FLEXIBLE` ($0.25$). Total dimension ignoring is postponed to future releases.
- **No Direct Persistence Editing**: Profiles cannot be modified post-submission in MVP v1.
