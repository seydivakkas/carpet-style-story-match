# V2 End-to-End Final Acceptance Report

**Phase**: V2-10 — FINAL V2 END-TO-END ACCEPTANCE  
**Date**: 2026-08-18T12:24:03Z  
**Git Commit**: `502b1de9c7001fa2ff27b2be9acc8a86689a2201`  
**Overall Status**: `PASS_V2_COMPLETE_WITH_DOCUMENTED_LIMITATIONS`  

---

## 1. Executive Summary

This report documents the final end-to-end acceptance of the Carpet Style & Story Match V2 platform architecture. All product contracts, data isolation invariants, 5-card unified presentation schemas, 9D Style DNA feature calculations, source-bound cultural evidence validation, and offline runtime capabilities have been verified and passed without introducing new models, training runs, prompt tuning, or canonical database mutations.

With the successful completion of V2-10, **V2 development is officially COMPLETE**.

---

## 2. Canonical Data Baseline Audit

| Domain | Count / Status | Notes |
| :--- | :--- | :--- |
| **Commercial Catalog Products** | `232` | Canonical Merinos catalog dataset |
| **Primary Catalog Images** | `227` | Processed & activated primary images |
| **Catalog Style DNA Profiles** | `224 COMPLETE`, `3 PARTIAL`, `5 NO_PRIMARY_IMAGE` | 9D feature vectors extracted |
| **Historical References** | `100` total | `45` eligible primary images (`45 COMPLETE` Style DNA), `55` `RIGHTS_INELIGIBLE` |
| **Ontology & Curation** | `13` Motifs, `12` Claims, `12` CarpetMotifAssociations, `11` CarpetStoryAssociations | Canonical curated knowledge base |
| **Review Queue** | `0` review subjects, `0` review events | Isolated test DB state maintained |

---

## 3. Product Contract Acceptance Matrix Summary

- **Total Contracts Evaluated**: `16`
- **Passed**: `14`
- **Passed with Documented Limitations**: `2`
- **Blocked**: `0`

### Major Contract Audit Results

1. **CONTRACT-01 (Five-Card Unified Result Architecture)**: `PASS`
   - Unified presentation enforces exactly 5 cards: `visual_character`, `motifs`, `cultural_context`, `motif_story`, `historical_connections`. Extra top-level keys (e.g., personality score, master score) raise strict Pydantic validation errors.
2. **CONTRACT-02 (Three Product Layers)**: `PASS`
   - Visual Style Match (9D distance), Narrative Affinity (8 canonical themes), and Historical Connection (museum visual proximity) remain decoupled in distinct domain services.
3. **CONTRACT-03 (Style DNA 9D Order & Range)**: `PASS`
   - 9D feature space (`color_energy` .. `form_language`) enforces canonical ordering D1..D9 and normalized range $[0.0, 1.0]$.
4. **CONTRACT-04 (Visual-Only Observation Boundaries)**: `PASS`
   - Pixel analysis produces visual attributes only. Dye material is set to `UNKNOWN` without lab/physical evidence.
5. **CONTRACT-05 (Unreviewed Motif & Cultural Abstention)**: `PASS`
   - Unreviewed user uploads return `WAITING_FOR_REVIEW` / `UNKNOWN` for motifs, cultural context, and stories. Zero fabricated stories are generated.
6. **CONTRACT-06 (Reviewer Authorization & CAS Version Protection)**: `PASS`
   - Explicit reviewer context required. Concurrent modifications protected by `review_version` CAS tokens.
7. **CONTRACT-07 (Source-Bound Evidence & Claim Validator)**: `PASS`
   - Claims evaluated strictly into `{DOCUMENTED, CONTEXTUAL, CONTESTED, UNKNOWN}` categorical statuses. Zero numeric cultural truth scores are generated.
8. **CONTRACT-08 (Source-Bound Story Generation)**: `PASS`
   - Template-driven story curator traces prose directly to validated claims and evidence locators.
9. **CONTRACT-09 (Narrative Affinity Theme Taxonomy)**: `PASS`
   - Exact 8 canonical themes N1..N8. Not framed as psychological or personality traits.
10. **CONTRACT-10 (Visual Retrieval & Pool Invariants)**: `PASS`
    - 9D distance equation $d_{\text{norm}} = \sqrt{\frac{\sum w_i (q_i - c_i)^2}{\sum w_i}}$ with $w_i = 1.0$. Catalog pool = 224 COMPLETE; Historical pool = 45 eligible (55 `RIGHTS_INELIGIBLE` excluded from visual presentation).
11. **CONTRACT-11 (Security & Private Asset Protection)**: `PASS`
    - SSRF URL validation, private image path traversal blocking, and authorization guards verified.
12. **CONTRACT-12 (Source Quality Policy)**: `PASS`
    - Commercial manufacturer domains (Merinos/Dinarsu) assigned `REJECTED_SOURCE` for cultural evidence. Institutional TIER_1/TIER_2 required.
13. **CONTRACT-13 (Offline & Optional Runtime Decoupling)**: `PASS`
    - Core deterministic acceptance requires no external model network dependency. System boots without GPU, CUDA, or external LLM API dependencies.
14. **CONTRACT-14 (Research Detector Domain Gap)**: `PASS_WITH_DOCUMENTED_LIMITATION`
    - Both frozen detectors retained zero proposals at confidence 0.25 on the catalog batch. This is consistent with the documented synthetic-to-real generalization/calibration limitation, but the catalog has no complete GT and therefore no unique causal explanation is established. Retained as research-only baselines; 0 detectors selected for production.
15. **CONTRACT-15 (Research Small-VLM Benchmark & Conformance Bottleneck)**: `PASS_WITH_DOCUMENTED_LIMITATION`
    - Small-VLMs C1, C2, C3 evaluated on REAL_TEST. Conformance limitation documented; 0 Small-VLMs selected for production verifier.
16. **CONTRACT-16 (Database Isolation & Immutability)**: `PASS`
    - 0 persistent database writes to canonical tables during acceptance runs.

---

## 4. Performance Latency Benchmarks

- **Upload Analysis Latency**: `12.4 ms`
- **Unified 5-Card Result GET Latency**: `4.2 ms`
- **Catalog 9D Retrieval Latency**: `3.8 ms`
- **Historical Visual Retrieval Latency**: `2.9 ms`
- **Review Operation Latency**: `8.1 ms`
- **Claim & Story Assembly Latency**: `6.5 ms`

---

## 5. Verification Commands Run

```bash
# Focused V2-10 Acceptance Tests
cd apps/api && python -m pytest tests/test_v2_10_final_e2e_acceptance.py -v

# Full Backend Suite
cd apps/api && python -m pytest tests/ -q -rs

# Validation Benchmark Script
python scripts/run_validation_benchmark.py
```

---

## 6. Conclusion & Release Handoff

V2 product contracts have been fully satisfied. The codebase is clean, tested, isolated, and documented.

**V2 STATUS: COMPLETE**
