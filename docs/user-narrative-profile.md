# User Narrative Profile Specification (v1)

## 1. Purpose & Core Invariants

The **User Narrative Profile** captures explicit user interest in the 8 canonical Narrative Themes ($N_1 \dots N_8$).

- Version identifier: `user-narrative-profile-v1`
- Canonical Turkish label: `Kullanıcı Anlatı Profili`

> [!CRITICAL]
> **CRITICAL SEMANTIC SEPARATIONS & NO INFERENCE**:
> - `NARRATIVE INTEREST != PERSONALITY / VISUAL STYLE PREFERENCE / IMPORTANCE / PSYCHOLOGICAL TRAIT`.
> - Narrative Interest is derived **ONLY** from explicit user selection. ZERO system inference!
> - No theme is ever inferred from 9D preference values, confidence, importance weights, visual style match scores, visual A/B responses, carpet Style DNA, or carpet metadata.

---

## 2. Frozen 8 Narrative Themes & Canonical Order

Every API and profile response returns themes in this exact $N_1 \dots N_8$ canonical order:

1. `nature_growth` ("Doğa & Büyüme") - N1
2. `belonging_home` ("Aidiyet & Yuva") - N2
3. `journey_discovery` ("Yolculuk & Keşif") - N3
4. `continuity_connection` ("Süreklilik & Bağ") - N4
5. `balance_order` ("Denge & Düzen") - N5
6. `renewal_transformation` ("Yenilenme & Dönüşüm") - N6
7. `tradition_craft` ("Gelenek & Zanaat") - N7
8. `cultural_heritage` ("Kültürel Miras") - N8

---

## 3. Interest Levels & Weights

- `PRIMARY`: weight `1.00`
- `SECONDARY`: weight `0.60`
- `NOT_SELECTED`: weight `0.00`

> [!NOTE]
> `interest_weight` measures narrative interest level, NOT importance profile weight or preference value. No negative weights are permitted (`interest_weight < 0` is forbidden).

---

## 4. Selection Rules & Validation

1. **Max Primary**: $\le 3$ themes (`primary_themes`).
2. **Max Secondary**: $\le 3$ themes (`secondary_themes`).
3. **Explicit Selection Minimum**: If `skip = false`, at least 1 theme must be selected in `primary_themes` or `secondary_themes`. Empty selection $\to$ `422 NARRATIVE_SELECTION_EMPTY`.
4. **Primary is Not Required**: `primary_themes = []`, `secondary_themes = ["tradition_craft"]` with `skip = false` is VALID.
5. **Overlap Forbidden**: A theme cannot be in both `primary_themes` and `secondary_themes` $\to$ `422 NARRATIVE_SELECTION_OVERLAP`.
6. **Duplicates Forbidden**: Duplicate theme keys in request arrays $\to$ `422 NARRATIVE_SELECTION_DUPLICATE`.
7. **Unknown Themes**: Keys outside the 8 canonical themes $\to$ `422 NARRATIVE_SELECTION_UNKNOWN_THEME`.
8. **Skip Semantics**:
   - `skip = true` requires `primary_themes = []` and `secondary_themes = []`. If themes are provided with `skip = true` $\to$ `422 NARRATIVE_SKIP_CONFLICT`.
   - Results in all 8 themes as `NOT_SELECTED` (weight `0.00`), `completion_mode = SKIPPED`.
   - `SKIPPED` means "User opted not to select narrative themes". It does NOT mean dislike or negative preference. In future tasks, `SKIPPED` means Narrative Affinity is `NOT_AVAILABLE`.

---

## 5. Precondition & Independence

- Precondition: Requires `UserPreferenceProfile.status == REVIEWED` (`409 NARRATIVE_PROFILE_REQUIRES_REVIEWED_PREFERENCE_PROFILE`).
- `ImportanceProfile` is **NOT** required.
- Assessment status is **NOT** modified by narrative profile creation (e.g., `IMPORTANCE_COMPLETE` stays `IMPORTANCE_COMPLETE`), preserving existing lifecycle & GÖREV 08 Style Match behavior.

---

## 6. Immutability & Idempotency

- `UserNarrativeProfile` is immutable in MVP v1.
- Identical request returns existing profile (Idempotent 200/201 response).
- Different second request returns `409 NARRATIVE_PROFILE_ALREADY_EXISTS`.

---

## 7. Database Persistence & API Endpoints

- Tables: `user_narrative_profiles` and `user_narrative_themes` (exactly 8 snapshot rows per profile).
- Endpoints:
  - `POST /api/v1/preference-assessments/{assessment_id}/narrative-profile`
  - `GET /api/v1/preference-assessments/{assessment_id}/narrative-profile`
  - `GET /api/v1/meta/narrative-profile`

---

## 8. Known Limitations

- **No Narrative Affinity**: Narrative Affinity calculation will be added in future tasks using curated motif story evidence.
- **No Motif Stories / Historical Attribution**: Curated motif story models and historical attribution are out of scope for GÖREV 09.
