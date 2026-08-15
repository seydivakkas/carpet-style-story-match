# Multimodal User Preference Profile & Confidence Specification (v1)

## 1. Overview & Purpose

The **Multimodal User Preference Profile** synthesizes text-based qualitative preferences (`TextPreferenceProfile`) and visual stimulus preferences (`VisualPreferenceProfile`) into a canonical 9D User Preference Profile ($D_1 \dots D_9$) paired with a parallel **Preference Confidence Profile** ($C_1 \dots C_9$).

It introduces the **User Review & Override Lifecycle** allowing explicit user declaration over system inference.

---

## 2. Core Domain Invariants & Separation

1. **Preference $\ne$ Confidence**: Preference measures *what* the user prefers ($0.0 \dots 1.0$). Confidence measures *how reliable and consistent* the underlying evidence is ($0.0 \dots 1.0$). A high preference (e.g., $0.90$) with low confidence (e.g., $0.15$) is a valid and meaningful state.
2. **Confidence $\ne$ Importance**: Confidence is purely an evidence measurement metric. It is NEVER used to weight preferences or substitute for user importance.
3. **Preference $\ne$ Personality**: The profile measures aesthetic design preferences, not psychological personality traits.
4. **User Override $\ne$ System Inference**: User overrides modify `final_value` and set `provenance = USER_OVERRIDDEN`. The original `inferred_value` and `confidence` remain untouched.

---

## 3. Canonical 9D Dimension Coverage & Multimodal Aggregation

### Version Constants
- `MULTIMODAL_PREFERENCE_VERSION`: `multimodal-preference-v1`
- `PREFERENCE_CONFIDENCE_VERSION`: `preference-confidence-v1`

### Modality Sources per Dimension

| Dim | Key | Text Weight | Visual Weight | Aggregation Method | Expected Status |
|---|---|---|---|---|---|
| $D_1$ | `color_energy` | 1.00 | 1.00 | Weighted Average $\frac{1.0 \cdot T + 1.0 \cdot V}{2.0}$ | `MEASURED` |
| $D_2$ | `color_diversity` | 1.00 | 0.00 | Text-only ($T_2$) | `MEASURED` |
| $D_3$ | `contrast` | 1.20 | 1.00 | Weighted Average $\frac{1.2 \cdot T + 1.0 \cdot V}{2.2}$ | `MEASURED` |
| $D_4$ | `warmth` | 1.00 | 0.00 | Text-only ($T_4$) | `MEASURED` |
| $D_5$ | `visual_complexity` | 0.00 | 1.00 | Visual-only ($V_3$) | `MEASURED` |
| $D_6$ | `structural_order` | 1.00 | 1.00 | Weighted Average $\frac{1.0 \cdot T + 1.0 \cdot V}{2.0}$ | `MEASURED` |
| $D_7$ | `rhythm_repetition` | 0.00 | 1.00 | Visual-only ($V_5$) | `MEASURED` |
| $D_8$ | `focal_strength` | 0.25 (weak) | 0.00 | Text-only ($T_1$) | `MEASURED` |
| $D_9$ | `form_language` | 1.00 | 1.00 | Weighted Average $\frac{1.0 \cdot T + 1.0 \cdot V}{2.0}$ | `MEASURED` |

---

## 4. Confidence Profile Formula (v1)

### Case A — Both Text & Visual Measured ($D_1, D_3, D_6, D_9$)
$$\text{source\_coverage} = \frac{\min(\text{text\_w}, 1.0) + \min(\text{visual\_w}, 1.0)}{2}$$
$$\text{agreement} = 1.0 - |T_i - V_i|$$
$$\text{confidence} = 0.25 \times \text{source\_coverage} + 0.75 \times \text{agreement}$$

- **High Agreement**: $T = 0.80, V = 0.80 \implies \text{agreement} = 1.00, \text{confidence} = 1.00$.
- **Strong Conflict**: $T = 0.00, V = 1.00 \implies \text{agreement} = 0.00, \text{confidence} = 0.25$.

### Case B — Single Modality Measured ($D_2, D_4, D_5, D_7, D_8$)
$$\text{confidence} = 0.60 \times \min(\text{weight}, 1.0)$$
- **Strong Single Source** ($D_2, D_4, D_5, D_7$, weight 1.0): $\text{confidence} = 0.60$.
- **Weak Single Source** ($D_8$, weight 0.25): $\text{confidence} = 0.60 \times 0.25 = \mathbf{0.15}$.

### Case C — No Evidence
- $\text{confidence} = \text{None}$, $\text{status} = \text{NO\_EVIDENCE}$.

---

## 5. Provenance & Lifecycle Management

### Provenance Values
- `INFERRED`: Calculated by system multimodal aggregation.
- `USER_CONFIRMED`: Explicitly accepted by user during review.
- `USER_OVERRIDDEN`: Explicitly modified by user.

### Lifecycle Status Progression
$$\text{TEXT\_PENDING} \to \text{TEXT\_COMPLETE} \to \text{VISUAL\_PENDING} \to \text{VISUAL\_COMPLETE} \to \text{PROFILE\_READY} \to \text{PROFILE\_REVIEWED}$$

- `POST /build-profile` requires status $\ge \text{VISUAL\_COMPLETE}$. Moves status to `PROFILE_READY`.
- `PUT /dimensions/{key}` allows updating `final_value` while profile is `DRAFT` / `PROFILE_READY`.
- `POST /confirm-profile` transitions `INFERRED` dimensions to `USER_CONFIRMED`, locks profile, and sets status to `PROFILE_REVIEWED`.
- `PROFILE_REVIEWED` profiles are **immutable** (`409 PREFERENCE_PROFILE_ALREADY_REVIEWED`).

---

## 6. Known Limitations

- **Psychometric Disclaimer**: Confidence v1 is a deterministic engineering heuristic, not a calibrated psychometric measurement.
- **Modality Coverage Gaps**: $D_2/D_4$ are text-only; $D_5/D_7$ are visual-only; $D_8$ has only weak text evidence ($w=0.25$).
- **Override Scope**: User override reflects explicit declaration and does not retroactively alter system evidence confidence.
