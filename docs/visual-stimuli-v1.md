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
2. **Max Non-Target Delta**: $\max_{i \ne \text{target}} |B_i - A_i| \le 0.15$
3. **Decoupling Invariant**: $V_4$ ($D_6$ target) must not contaminate $D_7$ ($\le 0.10$). $V_5$ ($D_7$ target) must not contaminate $D_6$ ($\le 0.10$).
4. **CV Engine Validation Rule**: Measured Style DNA values from `StyleDNAEngine.analyze_image()` must satisfy $B_{\text{target}} > A_{\text{target}}$ for all 6 cards.
