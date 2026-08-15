# VALIDATION, CALIBRATION & END-TO-END BENCHMARK v1

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## 1. Overview & Purpose

The **Validation, Calibration & End-to-End Benchmark v1** subsystem provides an automated, deterministic quality guardrail for the Carpet Style & Story Match platform. It rigorously verifies algorithm invariants, preference matrices, computer vision Style DNA calibrations, narrative affinity projections, historical reference connections, abstention rules, and cross-layer metric independence.

Key System Invariant:
> **NO HIDDEN FAILURES (RULE 7)**: Required benchmark check failures CANNOT be masked or swallowed. Any single required check failure sets the overall benchmark status to `FAIL` and returns exit code 1.

---

## 2. Benchmark Check Group Inventory (38 Checks)

The benchmark suite consists of 38 comprehensive checks organized into 15 domain groups:

| Group ID | Domain | Check Count | Required | Description |
|---|---|---|---|---|
| **GROUP_A** | Frozen Contracts | 5 | 5 | Verifies 9D Style DNA order, 8 Narrative Themes order, Importance weights, Narrative weights, and D6!=D7 invariant. |
| **GROUP_B** | Style DNA & Visual Stimuli | 5 | 5 | Range & bounding [0, 1], determinism, SHA-256 asset hashes, V1..V6 target delta & contamination, negative validator regression. |
| **GROUP_C** | Text Preference Matrix | 4 | 4 | 6 questions count, D5 & D7 NOT_MEASURED rule, D8 weak weight=0.25, [-1.0, +1.0] polarity scale. |
| **GROUP_D** | Visual Preference Catalog | 1 | 1 | 6 visual stimuli cards catalog contract. |
| **GROUP_E** | Multimodal & Confidence | 4 | 4 | 9/9 completed profile coverage, D3 weighted merge arithmetic, confidence formula cases, user override provenance preservation. |
| **GROUP_F** | Importance Profile | 2 | 2 | Default skip profile (9x STANDARD=0.60), priority/flexible overlap rejection. |
| **GROUP_G** | Visual Style Match | 4 | 4 | Exact identity baseline (100.0 VERY_STRONG), polar difference baseline (20.0 LOW), priority weight sensitivity, <70% coverage abstention. |
| **GROUP_H** | User Narrative Profile | 1 | 1 | Theme weights & defaults (1.00 / 0.60 / 0.00). |
| **GROUP_K** | Narrative Affinity | 3 | 3 | Golden case (0.375 MODERATE), contested-only evidence abstention, user skipped profile abstention. |
| **GROUP_L** | Historical Source Type | 1 | 1 | Historical source_type='HISTORICAL' and primary_reference_type='MUSEUM_OBJECT'. |
| **GROUP_M** | Historical Connection | 3 | 3 | Golden case (1.00 VERY_CLOSE), <6 dimensions coverage abstention, non-attribution contract (no probability/authenticity scores). |
| **GROUP_N** | Cross-Layer Independence | 2 | 2 | Metric independence between Style Match and Narrative Affinity; 3-axis evaluation invariant (no combined/total score). |
| **GROUP_O** | Abstention Correctness | 1 | 1 | 100% abstention correctness when evidence is missing or skipped. |
| **GROUP_P** | Determinism & Hashes | 1 | 1 | Narrative evidence snapshot hash sorting invariance. |
| **GROUP_R** | Security & Persistence | 1 | 1 | Server-owned calculated values security protection (no client injection of scores/weights/confidence). |

---

## 3. Threshold Inventory & Asset Hashes

### Thresholds
- **STYLE_DNA_DETERMINISM_TOLERANCE**: `1e-4`
- **STIMULUS_MIN_TARGET_DELTA**: `0.35`
- **STIMULUS_MAX_NON_TARGET_CONTAMINATION**: `0.15`
- **STYLE_MATCH_MIN_WEIGHTED_COVERAGE**: `0.70` (70%)
- **STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS**: `6`
- **HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS**: `6`

### Visual Stimulus SHA-256 Hashes
- `v1_color_energy_a.svg`: `da16f4adbf8c20575d278aa7c191a6134bdf8bb8f000305ca78eb6be9a35e0ce`
- `v1_color_energy_b.svg`: `1e5086d991b5c219154f8b22a00fe4ef19f9bb49ec012845c08cd9aaedfa9b36`
- `v2_contrast_a.svg`: `bf5aeaa5bd9986bbfbc4ca944d18ec069fdf5851b473ef7b539c2c589b2512f4`
- `v2_contrast_b.svg`: `a6ec15446aa27ed7c093a1c2afb5ee68112521a0cc4a9bb5fce61bf968b598ff`
- `v3_visual_complexity_a.svg`: `aeefbcf3ce3e08f5154aa143e9ec2d75a61138b36eaefaafe44747ebc796ae77`
- `v3_visual_complexity_b.svg`: `a9a6225b1fca8305c48fd392f4422e032906ed5377f0a6d13ffb7a44f5139c27`
- `v4_structural_order_a.svg`: `dbf588c5efbce19dbccb5ee57f3604f5e7149a4eec9c3aeebaf1df3fe61bfb41`
- `v4_structural_order_b.svg`: `2be589c3726a45ef92e316a75f0a07204f1df91ff248ddb5650aa7383f98246f`
- `v5_rhythm_repetition_a.svg`: `7513360b8d7ef20857ac0ac11fec84e318ee4ebfe3ea5ffae4d2217c2fbc9fb8`
- `v5_rhythm_repetition_b.svg`: `e463bd9b3bfe8faeddbd3dddf58544e31f0f9c2d7658ee6e1a49abddbbfa73b5`
- `v6_form_language_a.svg`: `c71a3962b7ae4d3c3fb2bcaea1efeeea62b3226dbab8cf8073b64bc7df53b80b`
- `v6_form_language_b.svg`: `3ea0aa125e1a1796cfbfa85d263b65ef3df6c6eb0d1487bb0efc3ee8ef01fdf4`

---

## 4. Execution & CLI Usage

### Benchmark CLI Script
```bash
python -m app.scripts.run_validation_benchmark --output artifacts/validation/benchmark-report.json
```

### Pytest Integration
```bash
pytest tests/test_validation_benchmark.py
pytest tests/e2e/test_full_product_flow.py
pytest
```
