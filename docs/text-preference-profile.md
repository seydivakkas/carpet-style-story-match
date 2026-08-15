# Text Preference Profile & Assessment Specification

## 1. Overview & Principles

- **Evidence Version**: `text-preference-evidence-v1`
- **Identity Scope**: Anonymous `PreferenceAssessment` identified by UUID v4 (no authentication or user account required).
- **Statuses**: `TEXT_PENDING`, `TEXT_COMPLETE`.

> **FROZEN PRINCIPLE**:
> **USER PREFERENCE $\neq$ PERSONALITY**. Aesthetic preferences represent visual and spatial design inclinations, not psychological character traits. Terms like "introvert", "extrovert", or "personality type" are strictly forbidden.

---

## 2. Response Scale & Mapping

Each of the 6 text preference cards accepts one of five canonical choices:

| Choice | Canonical Numeric Value ($R_q$) | Meaning |
| :--- | :---: | :--- |
| `STRONGLY_A` | $-1.00$ | Strong preference for Option A |
| `SLIGHTLY_A` | $-0.50$ | Slight preference for Option A |
| `NEUTRAL` | $0.00$ | Balanced / No direction preference |
| `SLIGHTLY_B` | $+0.50$ | Slight preference for Option B |
| `STRONGLY_B` | $+1.00$ | Strong preference for Option B |

> **INVARIANT**: Response values ($-1 \dots +1$) reflect preference direction on a question card, not Style DNA scores.

---

## 3. Canonical 6 Text Preference Cards

1. **`T1_ROOM_ROLE`** (Color Energy / Room Role):
   - *Prompt (TR)*: Bir halının odadaki rolü sana hangisiyle daha yakın geliyor?
   - *Option A*: Ortama sakin biçimde uyum sağlaması.
   - *Option B*: Mekânda daha canlı ve dikkat çekici bir etki oluşturması.
   - *Target Weights*: $D_1 = 1.00, D_3 = 0.20, D_8 = 0.25$.

2. **`T2_COLOR_DIVERSITY`** (Color Diversity):
   - *Prompt (TR)*: Bir halıda renk kullanımı açısından hangisini daha çok tercih edersin?
   - *Option A*: Az sayıda ve kontrollü renk.
   - *Option B*: Daha zengin ve çeşitli renk paleti.
   - *Target Weights*: $D_2 = 1.00$.

3. **`T3_CONTRAST`** (Contrast):
   - *Prompt (TR)*: Desen ve renk geçişlerinde hangisi sana daha yakın?
   - *Option A*: Daha yumuşak ve birbirine yaklaşan geçişler.
   - *Option B*: Daha belirgin ve güçlü ayrımlar.
   - *Target Weights*: $D_3 = 1.00$.

4. **`T4_WARMTH`** (Warmth):
   - *Prompt (TR)*: Renk atmosferinde hangisini daha çok tercih edersin?
   - *Option A*: Mavi, turkuaz ve serin tonların öne çıktığı bir atmosfer.
   - *Option B*: Kırmızı, turuncu, sarı ve sıcak tonların öne çıktığı bir atmosfer.
   - *Target Weights*: $D_4 = 1.00$.

5. **`T5_STRUCTURAL_ORDER`** (Structural Order):
   - *Prompt (TR)*: Kompozisyon düzeninde hangisi sana daha yakın?
   - *Option A*: Daha serbest, asimetrik ve beklenmedik yerleşimler.
   - *Option B*: Daha dengeli, düzenli ve simetrik yerleşimler.
   - *Target Weights*: $D_6 = 1.00$.
   - *Note*: **T5 DOES NOT measure $D_7$ (Rhythm & Repetition)**.

6. **`T6_FORM_LANGUAGE`** (Form Language):
   - *Prompt (TR)*: Desenlerin biçim dili açısından hangisini daha çok tercih edersin?
   - *Option A*: Köşeli, doğrusal ve geometrik formlar.
   - *Option B*: Kıvrımlı, akışkan ve organik formlar.
   - *Target Weights*: $D_9 = 1.00$.

---

## 4. Evidence Matrix & Aggregation

### 6×9 Evidence Weight Matrix

$$\begin{pmatrix}
1.00 & 0.00 & 0.20 & 0.00 & 0.00 & 0.00 & 0.00 & 0.25 & 0.00 \\
0.00 & 1.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 \\
0.00 & 0.00 & 1.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 \\
0.00 & 0.00 & 0.00 & 1.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 \\
0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 1.00 & 0.00 & 0.00 & 0.00 \\
0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 0.00 & 1.00
\end{pmatrix}$$

### Directional Weight & Value Conversion

For dimension $i$:
$$\bar{W}_i = \frac{\sum_{q \in Q_i} R_q \cdot w_{qi}}{\sum_{q \in Q_i} w_{qi}}$$

Preference score $P_i \in [0.0, 1.0]$:
$$P_i = \frac{\bar{W}_i + 1}{2}$$

### Measured vs Unmeasured Coverage
- **`MEASURED`**: $D_1, D_2, D_3, D_4, D_6, D_8, D_9$.
- **`NOT_MEASURED`**: $D_5$ (Visual Complexity) and $D_7$ (Rhythm & Repetition) have total evidence weight $0.0$. They are set to `value = None` and `status = NOT_MEASURED`.

> **INVARIANT**: Neutral response ($R_q = 0.0$) produces a valid preference value $P_i = 0.50$ (`MEASURED`). Missing evidence produces `value = None` (`NOT_MEASURED`).

---

## 5. Database Persistence Models

1. `PreferenceAssessmentModel`: Stores assessment UUID, status (`TEXT_PENDING` / `TEXT_COMPLETE`), evidence version, and timestamps.
2. `TextPreferenceResponseModel`: Stores user choices ($R_q \in [-1.0, +1.0]$) for each of the 6 text questions per assessment.
3. `TextPreferenceProfileModel`: Stores overall text profile record.
4. `TextPreferenceDimensionModel`: Stores 9 canonical dimension records (`MEASURED` vs `NOT_MEASURED`) per profile.

---

## 6. Known Limitations

1. **Partial Text Coverage**: Text questions do not directly measure $D_5$ or $D_7$.
2. **Weak Secondary Evidence for $D_8$**: Focal strength is weakly measured via $T_1$ ($w=0.25$) and will be refined during visual A/B testing in GÖREV 05.
3. **No Cross-Modal Confidence**: Confidence profiles ($C_1 \dots C_9$) will be introduced in GÖREV 06 when combining text and visual evidence.
