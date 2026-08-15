# Frozen 9D Carpet Style DNA Specification

The 9D Style DNA is the canonical vector representation used for visual style distance calculations. The order and identifiers below are frozen and immutable.

## Dimension Specifications

| Code | Canonical Identifier | Turkish UI Label | Low Range (0.0) | High Range (1.0) |
|---|---|---|---|---|
| **D1** | `color_energy` | Renk Enerjisi | Sakin | Canlı |
| **D2** | `color_diversity` | Renk Çeşitliliği | Sınırlı Palet | Zengin Palet |
| **D3** | `contrast` | Kontrast | Yumuşak | Güçlü |
| **D4** | `warmth` | Renk Sıcaklığı | Soğuk | Sıcak |
| **D5** | `visual_complexity` | Görsel Karmaşıklık | Sade | Detaylı |
| **D6** | `structural_order` | Düzen & Simetri | Serbest | Düzenli |
| **D7** | `rhythm_repetition` | Ritim & Tekrar | Tekil | Ritmik/Tekrarlı |
| **D8** | `focal_strength` | Odak Gücü | Dağıtılmış | Güçlü Odak |
| **D9** | `form_language` | Form Dili | Geometrik | Organik |

## Rules & Constraints

1. **Strict Order**: D1 → D9 must be preserved in all array representations, database serializations, and API schemas.
2. **Normalized Scale**: All dimensions are strictly normalized floating-point numbers between `0.0` and `1.0`.
3. **No Dynamic Additions**: Custom or extra style dimensions cannot be added dynamically without updating this contract version.
