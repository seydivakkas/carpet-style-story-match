# Visual Preference Profile & Controlled Stimulus Specification v1

## 1. Overview & Versioning

- **Stimulus Version**: `visual-preference-stimuli-v1`
- **Evidence Version**: `visual-preference-evidence-v1`
- **Card Count**: Exactly 6 Controlled Visual A/B Cards ($V_1 \dots V_6$)
- **Target Dimensions**: $D_1, D_3, D_5, D_6, D_7, D_9$

> **CONTROLLED STIMULUS PRINCIPLE**:
> Each visual card varies strictly its target Style DNA dimension while keeping non-target dimensions as constant as possible ($\text{target\_delta} \ge 0.35$, $\text{max\_non\_target\_delta} \le 0.15$). No real carpet photos, rooms, furniture, brand names, or historical labels are used to prevent confounding bias.

---

## 2. Canonical Card Mapping & Stimulus Pairs

| Card Key | Name | Target Dimension | Variant A (Low Pole) | Variant B (High Pole) | Base Family |
|---|---|---|---|---|---|
| `V1_COLOR_ENERGY` | Color Energy | $D_1$ `color_energy` | Calm / muted chroma | Vivid / energetic chroma | `BASE_A` Medallion |
| `V2_CONTRAST` | Contrast | $D_3$ `contrast` | Soft separation | Strong separation | `BASE_B` All-over |
| `V3_VISUAL_COMPLEXITY` | Visual Complexity | $D_5$ `visual_complexity` | Simple geometry | Detailed micro-decoration | `BASE_C` Banded |
| `V4_STRUCTURAL_ORDER` | Structural Order | $D_6$ `structural_order` | Asymmetric / free arrangement | Symmetric / ordered arrangement | `BASE_A` Medallion |
| `V5_RHYTHM_REPETITION` | Rhythm & Repetition | $D_7$ `rhythm_repetition` | Same positions, varied motifs | Same positions, identical repeated motif | `BASE_B` All-over |
| `V6_FORM_LANGUAGE` | Form Language | $D_9$ `form_language` | Angular / polygonal | Curvilinear / organic | `BASE_C` Banded |

---

## 3. Presentation Randomization & Security

- **Server-Side Side Assignment**: For each assessment and card, the server randomly assigns variant A or B to the `LEFT` or `RIGHT` position upon starting the visual phase (`POST /api/v1/preference-assessments/{id}/start-visual`).
- **Assignment Persistence**: Side assignments are persisted in `visual_preference_presentations` and remain immutable for that assessment.
- **Client Polarity Obfuscation**: The client receives only `left_asset_url` and `right_asset_url`. The semantic A/B identity of each side is hidden from the client.
- **Display Response Scale**:
  - `STRONGLY_LEFT` (display value -1.0)
  - `SLIGHTLY_LEFT` (display value -0.5)
  - `NEUTRAL` (display value 0.0)
  - `SLIGHTLY_RIGHT` (display value +0.5)
  - `STRONGLY_RIGHT` (display value +1.0)
- **Server-Side Polarity Resolution**:
  - If `LEFT = A` and `RIGHT = B`: `STRONGLY_LEFT` $\to -1.0$, `STRONGLY_RIGHT` $\to +1.0$
  - If `LEFT = B` and `RIGHT = A`: `STRONGLY_LEFT` $\to +1.0$, `STRONGLY_RIGHT` $\to -1.0$
  - `NEUTRAL` remains `0.0`.

---

## 4. Visual Evidence Matrix & Profile Coverage

The canonical 6×9 visual evidence matrix links choices to Style DNA dimensions:

$$W_{v, i} = \begin{cases} 1.0 & \text{if card } v \text{ targets dimension } i \\ 0.0 & \text{otherwise} \end{cases}$$

### Profile Coverage
- **Measured Dimensions**: $D_1, D_3, D_5, D_6, D_7, D_9$ (preference score $P_i = \frac{\text{canonical\_direction} + 1}{2} \in [0.0, 1.0]$)
- **Unmeasured Dimensions**: $D_2$ (color_diversity), $D_4$ (warmth), $D_8$ (focal_strength) have `value = None`, `status = NOT_MEASURED`, `evidence_weight = 0.0`, `evidence_count = 0`.

---

## 5. Assessment Status Lifecycle Extension

```
TEXT_PENDING → TEXT_COMPLETE → VISUAL_PENDING → VISUAL_COMPLETE
```

1. Visual phase requires `TEXT_COMPLETE` status. Calling `start-visual` before completing text phase returns `409 VISUAL_PHASE_REQUIRES_TEXT_COMPLETE`.
2. Completing visual phase (`POST complete-visual`) requires answering all 6 visual cards; otherwise returns `409 VISUAL_PREFERENCES_INCOMPLETE`.
3. Once `VISUAL_COMPLETE`, visual responses are locked against modifications (`409 VISUAL_PREFERENCES_ALREADY_COMPLETED`). Re-completing is idempotent.
