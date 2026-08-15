# Visual Preference Stimuli Catalog v1 (`visual-preference-stimuli-v1`)

## 1. Overview & Base Families

All controlled visual stimuli are top-down abstract carpet designs rendered procedurally in vector format. To avoid cultural and market bias, zero historical labels (e.g. Ottoman, Persian) or room/product contexts are used.

### Abstract Neutral Base Families
1. `BASE_A` (Abstract Medallion): Central ornamental motif surrounded by border framing.
2. `BASE_B` (Abstract All-Over): Grid-aligned or field-distributed repeating motifs.
3. `BASE_C` (Abstract Banded): Horizontal/vertical repeating geometric or curvilinear field bands.

---

## 2. Stimuli Specifications ($V_1 \dots V_6$)

### V1 — Color Energy (`V1_COLOR_ENERGY`)
- **Target Dimension**: $D_1$ `color_energy`
- **Base Family**: `BASE_A` (Abstract Medallion)
- **Variant A (Low Pole)**: Muted, low-chroma Earth tones (RGB [120, 115, 110], [90, 85, 80], [150, 145, 140]).
- **Variant B (High Pole)**: Energetic, high-chroma palette (RGB [210, 40, 30], [240, 180, 20], [30, 90, 180]).
- **Controlled Invariants**: Palette color count = 4, identical medallion topology, layout, edge structure, and symmetry.
- **Reference Vector Intent**:
  - Variant A: $D_1 = 0.15$, $D_2=0.40, D_3=0.50, D_4=0.50, D_5=0.40, D_6=0.85, D_7=0.50, D_8=0.70, D_9=0.50$
  - Variant B: $D_1 = 0.85$, $D_2=0.40, D_3=0.50, D_4=0.50, D_5=0.40, D_6=0.85, D_7=0.50, D_8=0.70, D_9=0.50$

### V2 — Contrast (`V2_CONTRAST`)
- **Target Dimension**: $D_3$ `contrast`
- **Base Family**: `BASE_B` (Abstract All-Over)
- **Variant A (Low Pole)**: Low luminance range, soft edge separation between motifs and ground (Luminance delta ~20%).
- **Variant B (High Pole)**: High luminance range, stark black/white/deep-blue edge separation (Luminance delta ~80%).
- **Controlled Invariants**: Identical motif count, layout grid, hue balance, and element shapes.
- **Reference Vector Intent**:
  - Variant A: $D_3 = 0.20$, others constant
  - Variant B: $D_3 = 0.85$, others constant

### V3 — Visual Complexity (`V3_VISUAL_COMPLEXITY`)
- **Target Dimension**: $D_5$ `visual_complexity`
- **Base Family**: `BASE_C` (Abstract Banded)
- **Variant A (Low Pole)**: Large bold geometric shapes, clean fields, zero internal micro-filler.
- **Variant B (High Pole)**: Same macro band structures with dense internal hatchings, sub-contour subdivisions, and micro-ornaments.
- **Controlled Invariants**: Macro layout, primary band positions, palette, symmetry, and repetition count.
- **Reference Vector Intent**:
  - Variant A: $D_5 = 0.15$, others constant
  - Variant B: $D_5 = 0.85$, others constant

### V4 — Structural Order (`V4_STRUCTURAL_ORDER`)
- **Target Dimension**: $D_6$ `structural_order`
- **Base Family**: `BASE_A` (Abstract Medallion)
- **Variant A (Low Pole)**: Asymmetric, organic displacement of elements, perturbed centroid, unaligned field accents.
- **Variant B (High Pole)**: Strictly dual-bilateral symmetric alignment, centered medallion, perfect 4-way quadrant balance.
- **Controlled Invariants**: Total motif count, palette, internal element complexity, and total coverage area.
- **Critical Decoupling Constraint**: $D_7$ (rhythm_repetition) delta must remain $\le 0.10$.
- **Reference Vector Intent**:
  - Variant A: $D_6 = 0.20$, others constant
  - Variant B: $D_6 = 0.90$, others constant

### V5 — Rhythm & Repetition (`V5_RHYTHM_REPETITION`)
- **Target Dimension**: $D_7$ `rhythm_repetition`
- **Base Family**: `BASE_B` (Abstract All-Over)
- **Variant A (Low Pole)**: 16 grid-positioned elements with 16 distinct unique motif shapes (varied identities).
- **Variant B (High Pole)**: 16 grid-positioned elements with 1 identical motif repeated across all 16 slots.
- **Controlled Invariants**: Spatial grid positions, total element count, color scheme, and global symmetry.
- **Critical Decoupling Constraint**: $D_6$ (structural_order) delta must remain $\le 0.10$.
- **Reference Vector Intent**:
  - Variant A: $D_7 = 0.15$, others constant
  - Variant B: $D_7 = 0.90$, others constant

### V6 — Form Language (`V6_FORM_LANGUAGE`)
- **Target Dimension**: $D_9$ `form_language`
- **Base Family**: `BASE_C` (Abstract Banded)
- **Variant A (Low Pole)**: Angular, polygonal, sharp 90°/45° straight-line geometric motifs.
- **Variant B (High Pole)**: Curvilinear, smooth, flowing organic wave and medallion motifs.
- **Controlled Invariants**: Macro band layout, motif sizes, color palette, contrast, and element count.
- **Reference Vector Intent**:
  - Variant A: $D_9 = 0.10$ (geometric)
  - Variant B: $D_9 = 0.90$ (organic)

---

## 3. Contamination Thresholds & Engine Validation Rules

1. **Target Delta**: $\text{target\_delta} = |B_{\text{target}} - A_{\text{target}}| \ge 0.35$
2. **Max Non-Target Delta**: $\max_{i \ne \text{target}} |B_i - A_i| \le 0.15$ (for decoupled structural dimensions).
3. **Decoupling Invariant**: $V_4$ ($D_6$ target) must not contaminate $D_7$ ($\le 0.15$). $V_5$ ($D_7$ target) must not contaminate $D_6$ ($\le 0.15$).
4. **CV Engine Validation Rule**: Measured Style DNA values from `StyleDNAEngine.analyze()` satisfy $B_{\text{target}} > A_{\text{target}}$ and $\text{target\_delta} \ge 0.35$ for all 6 cards.

---

## 4. Calibrated Measured Style DNA Values & Asset Hashes

| Card | Target Dim | Measured A | Measured B | Target Delta | Max Non-Target | Largest Non-Target | Validation | SHA-256 (A) | SHA-256 (B) |
|---|---|---|---|---|---|---|---|---|---|
| $V_1$ | `color_energy` ($D_1$) | 0.1038 | 1.0000 | **0.8962** | 0.1230 | warmth ($D_4$) | **PASS** | `36422f92d374ebfc84f2ed7a74ee2ff1c1d4d0d1152f99f0d59acea06af6747a` | `fceff54c8e4529cc1eee7ad558f2696f6c33cf34c87e9363c18863ccab1f4cab` |
| $V_2$ | `contrast` ($D_3$) | 0.2610 | 0.7915 | **0.5305** | 0.1119 | color_energy ($D_1$) | **PASS** | `f5f964612cbdf7744ff0b4f9251fb1e1f15e33809cc771c10b032a9be4575677` | `11d182175fab9ddafabae8c310ae84eccd0c01b365459f40538e1386b403dcb8` |
| $V_3$ | `visual_complexity` ($D_5$) | 0.3595 | 0.8204 | **0.4609** | 0.1348 | contrast ($D_3$) | **PASS** | `c181d953051a88811de34da3d9fb186c85ca0ff2ba754c94174a649fa05495f7` | `b896982ed5fe4e5f5ea6f596d67c90caeb3a8ab55a3a08599d65dff6b6fe8994` |
| $V_4$ | `structural_order` ($D_6$) | 0.6063 | 0.9943 | **0.3880** | 0.0221 | focal_strength ($D_8$) | **PASS** | `77c8bad3ccf96944ae2ad1cf02c9185aeb0ea2caa7361d42d4ed71fdb4b6eaae` | `f867720040889344798e61827238d449f993a9bd9d2f13a290a8d4b6680b1874` |
| $V_5$ | `rhythm_repetition` ($D_7$) | 0.5993 | 0.9719 | **0.3726** | 0.0706 | form_language ($D_9$) | **PASS** | `79f5cccf74630077d16242880c94cc431502f8fb9db05418f87ad1ec84bf6a8b` | `d0747b8f7ea25120ffd1d4e70a6b09b3d76ebaa7674671f8539a10f48dec2a87` |
| $V_6$ | `form_language` ($D_9$) | 0.4066 | 0.9922 | **0.5856** | 0.0826 | focal_strength ($D_8$) | **PASS** | `42a87b530c935359207111654c8dc31783e80b63ed7cf7c908216e1bfc1551cb` | `8f55af132a95a42965413d7bed4ffab1ce4302b0683681c2ade2cf4a04791a3d` |

