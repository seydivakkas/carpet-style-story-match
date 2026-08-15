# Visual Style Match Engine Specification (v1)

## 1. Overview & Purpose

The **Visual Style Match Engine** computes a quantitative, explainable **Visual Style Match Score** ($0.0 \dots 1.0$) between a reviewed `UserPreferenceProfile` (weighted by `ImportanceProfile`) and a `CarpetStyleProfile`.

- Version identifier: `visual-style-match-v1`
- Canonical Turkish label: `Görsel Stil Uyumu`

---

## 2. Frozen Semantic Boundaries

> [!IMPORTANT]
> This score measures **VISUAL STYLE MATCH ONLY**.
> It is **NOT**:
> - Personality score or psychological compatibility
> - Beauty or quality score
> - Purchase probability or commercial preference
> - Historical authenticity rating

---

## 3. Formulas

### Per-Dimension Similarity
For each canonical dimension $D_1 \dots D_9$:
$$\text{difference}_i = |\text{user\_final\_value}_i - \text{carpet\_value}_i| \quad \in [0.0, 1.0]$$
$$\text{similarity}_i = 1.0 - \text{difference}_i \quad \in [0.0, 1.0]$$

Weighted contribution:
$$\text{weighted\_similarity}_i = W_i \times \text{similarity}_i$$
$$\text{weighted\_difference}_i = W_i \times \text{difference}_i$$

Where $W_i \in \{1.00 \text{ (PRIORITY)}, 0.60 \text{ (STANDARD)}, 0.25 \text{ (FLEXIBLE)}\}$.

### Complete Match Score Formula
When all 9 canonical dimensions are comparable:
$$\text{VisualStyleMatchScore} = \frac{\sum_{i=1}^{9} W_i \times \text{similarity}_i}{\sum_{i=1}^{9} W_i}$$
$$\text{score\_100} = \text{score} \times 100.0$$

### Partial Match Score Formula & Coverage Policy
When a carpet profile is `PARTIAL` (some dimensions `NOT_AVAILABLE` or `FAILED`):
$$\text{partial\_score} = \frac{\sum_{i \in \text{comparable}} W_i \times \text{similarity}_i}{\sum_{i \in \text{comparable}} W_i}$$

$$\text{weighted\_coverage} = \frac{\sum_{i \in \text{comparable}} W_i}{\sum_{i=1}^{9} W_i}$$

**Coverage Threshold Policy**:
- Minimum weighted coverage: $\ge 0.70$ (`MATCH_MIN_WEIGHTED_COVERAGE`)
- Minimum comparable dimensions: $\ge 6$ (`MATCH_MIN_COMPARABLE_DIMENSIONS`)

---

## 4. Match Statuses & Product Labels

### Statuses
- `COMPLETE`: All 9 dimensions comparable.
- `PARTIAL`: $\ge 6$ comparable dimensions AND `weighted_coverage >= 0.70` (and $< 9$ dimensions).
- `NOT_AVAILABLE`: $< 6$ comparable dimensions OR `weighted_coverage < 0.70` (returns `score = None`, `score_100 = None`, `match_label = None`). No fake scores!

### Product Threshold Labels (v1)
- `score_100 >= 90.0` $\rightarrow$ `VERY_STRONG` ("Çok Güçlü Stil Eşleşmesi")
- `score_100 >= 75.0` $\rightarrow$ `STRONG` ("Güçlü Stil Eşleşmesi")
- `score_100 >= 60.0` $\rightarrow$ `MODERATE` ("Orta Düzey Stil Eşleşmesi")
- `score_100 >= 45.0` $\rightarrow$ `LIMITED` ("Sınırlı Stil Eşleşmesi")
- `< 45.0` $\rightarrow$ `LOW` ("Düşük Stil Eşleşmesi")

---

## 5. Confidence Invariant

> [!CRITICAL]
> **CONFIDENCE IS NOT MULTIPLIED INTO THE MATCH SCORE.**
> Preference confidence ($C_{\text{user}}$) and carpet measurement confidence ($C_{\text{carpet}}$) are stored strictly as **explanatory metadata** and do NOT alter similarity, dimension weights, or the overall match score.

---

## 6. Deterministic Explanation

No LLM dependencies are used. Explanations are strictly computed:
1. **Top Matches (Top 3)**: Ranked by $\text{match\_strength}_i = W_i \times \text{similarity}_i$ descending. Tie-broken by canonical $D_1 \dots D_9$ order.
2. **Main Differences (Top 2)**: Ranked by $\text{mismatch\_impact}_i = W_i \times \text{difference}_i$ descending. Narrative generated according to importance level (`PRIORITY`, `STANDARD`, `FLEXIBLE`).
3. **Coverage Notes**: Explains partial coverage or missing data reasons.
4. **Confidence Notes**: Highlights low-confidence evidence without penalizing score.

---

## 7. Database Persistence & API Endpoints

- `visual_style_match_results` & `visual_style_match_dimensions` (9 snapshot rows per match result).
- Endpoints:
  - `POST /api/v1/preference-assessments/{assessment_id}/style-matches` (Body: `{"carpet_style_profile_id": "uuid"}`)
  - `GET /api/v1/preference-assessments/{assessment_id}/style-matches/{match_id}`
  - `GET /api/v1/preference-assessments/{assessment_id}/style-matches`

---

## 8. Known Limitations

- **No Catalog Ranking / Search**: Computes match for 1 user profile vs 1 carpet profile. Catalog search/recommendations will be addressed in future tasks.
- **Minimum Weight 0.25**: Minimum weight is `FLEXIBLE` ($0.25$); complete dimension ignore (weight $0.0$) is not supported in MVP v1.
