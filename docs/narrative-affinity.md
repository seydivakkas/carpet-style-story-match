# Explainable Narrative Affinity Engine v1

## Status
- Version: `narrative-affinity-v1`
- Domain: Narrative Affinity & Story Alignment
- Implementation Status: Complete & Verified (`PASS`)

---

## 1. Executive Summary & Core Invariants

The **Explainable Narrative Affinity Engine v1** calculates a qualitative, explainable narrative affinity classification between a user's `UserNarrativeProfile` (GÖREV 09) and a catalog carpet's explicit `CarpetStoryAssociation` records (GÖREV 11).

### Core Architectural Invariants:
1. **ABSOLUTE SEPARATION OF NARRATIVE AFFINITY & VISUAL STYLE MATCH**:
   - Narrative Affinity is completely independent of Visual Style Match, Style DNA, Importance Profile, Preference Confidence, or user visual/text preferences.
   - Narrative Affinity MUST NEVER be combined into a single numeric score with visual match.
   - No numeric product score or percentage is exposed in Narrative Affinity responses.
2. **STRICT INPUT BOUNDARIES**:
   - **User Input**: ONLY `UserNarrativeProfile` (`PRIMARY` = 1.00, `SECONDARY` = 0.60, `NOT_SELECTED` = 0.00). Unselected user themes are completely excluded from the denominator.
   - **Carpet Input**: ONLY explicit `CarpetStoryAssociation` records linked to catalog carpets (`source_type == CATALOG`). Non-catalog carpets raise `NARRATIVE_AFFINITY_REQUIRES_CATALOG_CARPET`.
3. **NO AUTO-INHERITANCE**:
   - Claims attached to a motif are NOT auto-inherited by catalog carpets. Only explicit `CarpetStoryAssociation` records on the carpet are evaluated.
4. **CANONICAL 8 THEMES**:
   - All theme result lists and database theme rows preserve canonical N1 $\to$ N8 order (`nature_growth`, `belonging_home`, `journey_discovery`, `continuity_connection`, `balance_order`, `renewal_transformation`, `tradition_craft`, `cultural_heritage`).
5. **CATEGORICAL API CLASSIFICATION**:
   - Public API exposes `status` (`AVAILABLE`, `NOT_AVAILABLE`) and `affinity_level` (`VERY_STRONG`, `STRONG`, `MODERATE`, `LIMITED`).
6. **CLAIM STATUS & CONTESTED POLICY**:
   - `DOCUMENTED`: Confirmed theme support (`confirmed_match = True`).
   - `CONTEXTUAL`: Confirmed theme support (`confirmed_match = True`, with context/applicability notes).
   - `CONTESTED`: Does NOT enter confirmed numerator (`confirmed_match = False`). Tracked separately as `contested_overlap = True`.
   - `UNKNOWN`: Prohibited from providing positive evidence.
7. **SNAPSHOT & IDEMPOTENCY**:
   - DB table `narrative_affinity_results` enforces unique constraint on `(user_narrative_profile_id, carpet_id, carpet_narrative_snapshot_hash, affinity_version)`.
   - Exactly 8 theme snapshot rows are stored in `narrative_affinity_theme_results` per calculation.
8. **DETERMINISTIC ZERO-LLM EXPLANATIONS**:
   - Generated entirely via deterministic Turkish template prose and literature provenance sources.

---

## 2. Mathematical Definition

### 2.1 User Interest Weights
For each canonical theme $t \in \{N1, \dots, N8\}$:
$$
W_{user}(t) = \begin{cases} 
1.00 & \text{if } \text{interest\_level} = \text{PRIMARY} \\
0.60 & \text{if } \text{interest\_level} = \text{SECONDARY} \\
0.00 & \text{if } \text{interest\_level} = \text{NOT\_SELECTED}
\end{cases}
$$

Selected interest weight denominator:
$$
W_{selected} = \sum_{t \in \text{Selected}} W_{user}(t)
$$

### 2.2 Confirmed Interest Coverage Ratio
$$
\text{ConfirmedInterestCoverage} = \frac{\sum_{t \in \text{ConfirmedMatches}} W_{user}(t)}{W_{selected}}
$$

Where a theme $t$ is a `ConfirmedMatch` if and only if:
- $W_{user}(t) > 0$ (User selected $t$), AND
- $\text{CarpetSupportStatus}(t) \in \{\text{DOCUMENTED}, \text{CONTEXTUAL}\}$

### 2.3 Affinity Level Thresholds
$$
\text{AffinityLevel} = \begin{cases}
\text{VERY\_STRONG} & \text{if } \text{Coverage} \ge 0.80 \\
\text{STRONG} & \text{if } 0.60 \le \text{Coverage} < 0.80 \\
\text{MODERATE} & \text{if } 0.35 \le \text{Coverage} < 0.60 \\
\text{LIMITED} & \text{if } \text{Coverage} < 0.35
\end{cases}
$$

---

## 3. Availability & Not Available Reasons

Narrative Affinity status is `NOT_AVAILABLE` when:
1. `USER_NARRATIVE_SKIPPED`: User narrative profile completion mode is `SKIPPED`.
2. `NO_SELECTED_USER_THEMES`: User selected 0 themes ($W_{selected} == 0$).
3. `NO_CARPET_NARRATIVE_THEME_EVIDENCE`: Catalog carpet has 0 explicit story claims or 0 theme links.
4. `ONLY_CONTESTED_CARPET_EVIDENCE`: Carpet theme evidence consists exclusively of `CONTESTED` claims without any confirmed evidence.

---

## 4. API Endpoints

- `POST /api/v1/preference-assessments/{assessment_id}/narrative-affinities`: Compute or fetch existing idempotent narrative affinity for a catalog carpet.
- `GET /api/v1/preference-assessments/{assessment_id}/narrative-affinities/{affinity_id}`: Retrieve detailed affinity result with snapshot theme breakdown and explanations.
- `GET /api/v1/preference-assessments/{assessment_id}/narrative-affinities`: List all computed narrative affinity results for an assessment.
