# VALIDATION, CALIBRATION & END-TO-END BENCHMARK v1

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## 1. Overview & Purpose

The **Validation, Calibration & End-to-End Benchmark v1** subsystem provides an automated, deterministic quality release gate for the Carpet Style & Story Match platform. It strictly verifies algorithm invariants, preference matrices, computer vision Style DNA calibrations, motif knowledge provenance, carpet curation invariants, narrative affinity projections, historical reference connections, abstention rules, snapshot integrity, and cross-layer metric independence.

Key System Invariant:
> **NO HIDDEN FAILURES (RULE 7)**: Required benchmark check failures CANNOT be masked or swallowed. Any single required check failure sets the overall benchmark status to `FAIL` and returns exit code 1.

---

## 2. Benchmark Check Group Inventory (57 Checks)

The benchmark suite consists of 57 comprehensive checks organized into 20 domain groups:

| Group ID | Domain | Check Count | Required | Description |
|---|---|---|---|---|
| **GROUP_A** | Frozen Contracts | 5 | 5 | Verifies 9D Style DNA order, 8 Narrative Themes order, Importance weights, Narrative weights, and D6!=D7 invariant. |
| **GROUP_B** | Style DNA & Visual Stimuli | 5 | 5 | Range & bounding [0, 1], determinism, SHA-256 asset hashes, V1..V6 target delta & contamination, negative validator regression. |
| **GROUP_C** | Text Preference Matrix | 4 | 4 | 6 questions count, D5 & D7 NOT_MEASURED rule, D8 weak weight=0.25, [-1.0, +1.0] polarity scale. |
| **GROUP_D** | Visual Preference Catalog | 1 | 1 | 6 visual stimuli cards catalog contract. |
| **GROUP_E** | Multimodal & Confidence | 4 | 4 | 9/9 completed profile coverage, D3 weighted merge arithmetic, confidence formula cases, user override provenance preservation. |
| **GROUP_F** | Importance Profile | 2 | 2 | Default skip profile (9x STANDARD=0.60), priority/flexible overlap rejection. |
| **GROUP_G** | Visual Style Match | 5 | 5 | Exact identity baseline (100.0 VERY_STRONG), exact polar opposite baseline (0.0 LOW), priority weight sensitivity, <70% coverage abstention, boundary threshold assertions (90, 89.99, 75, 74.99, 60, 59.99, 45, 44.99). |
| **GROUP_H** | User Narrative Profile | 1 | 1 | Theme weights & defaults (1.00 / 0.60 / 0.00). |
| **GROUP_K** | Narrative Affinity | 3 | 3 | Golden case (0.375 MODERATE), contested-only evidence abstention, user skipped profile abstention. |
| **GROUP_I** | Motif Knowledge Provenance | 4 | 4 | DOCUMENTED (>=1 source), CONTEXTUAL (>=1 source & note), CONTESTED (>=2 sources & note), UNKNOWN (null text & 0 links, absence != UNKNOWN). |
| **GROUP_J** | Carpet Curation & Provenance | 4 | 4 | CURATOR_CONFIRMED/SOURCE_DOCUMENTED/UNCERTAIN notes & story constraints, CONTEXTUAL/CONTESTED applicability_note, non-auto-inheritance, two-layer provenance separation. |
| **GROUP_L** | Historical Source Type | 1 | 1 | Historical source_type='HISTORICAL' and primary_reference_type='MUSEUM_OBJECT'. |
| **GROUP_M** | Historical Connection | 3 | 3 | Golden case (1.00 VERY_CLOSE), <6 dimensions coverage abstention, non-attribution contract (no probability/authenticity scores). |
| **GROUP_N** | Cross-Layer Independence | 2 | 2 | Metric independence between Style Match, Narrative Affinity, and Historical Connection (5 parameter isolation checks); 3-axis evaluation invariant (no combined/total score). |
| **GROUP_O** | Abstention Correctness | 1 | 1 | 100% abstention correctness across 5 explicit missing/contested evidence scenarios. |
| **GROUP_P** | Determinism & Hashes | 1 | 1 | Narrative evidence snapshot hash sorting invariance. |
| **GROUP_Q** | Snapshot Integrity | 4 | 4 | 9D Visual Style Match rows, 8 Narrative Affinity theme rows, 9D Historical Connection rows, 0 orphan snapshot children invariant. |
| **GROUP_R** | Security & Persistence | 2 | 2 | Server-owned calculated values security protection (no client injection); path traversal, invalid MIME & oversize image guardrails. |
| **GROUP_S** | E2E Product Scenarios | 4 | 4 | E2E-1 Happy Path, E2E-2 Skip Path, E2E-3 Partial Data Path, E2E-4 Contested Knowledge Path. |
| **GROUP_T** | Migration Release Gate | 1 | 1 | Alembic fresh database 001->014 upgrade & downgrade/re-upgrade release gate PASS. |

---

## 3. Threshold Inventory & Asset Hashes

### Thresholds
- **STYLE_DNA_DETERMINISM_TOLERANCE**: `1e-4`
- **STIMULUS_MIN_TARGET_DELTA**: `0.35`
- **STIMULUS_MAX_NON_TARGET_CONTAMINATION**: `0.15`
- **STYLE_MATCH_MIN_WEIGHTED_COVERAGE**: `0.70` (70%)
- **STYLE_MATCH_MIN_COMPARABLE_DIMENSIONS**: `6`
- **HISTORICAL_CONNECTION_MIN_COMPARABLE_DIMENSIONS**: `6`

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
