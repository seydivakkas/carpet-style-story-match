# CHANGELOG

All notable changes to the **Carpet Style & Story Match** project are documented in this file.

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

---

## [1.0.0-rc.1] - 2026-08-15

### Added
- **9D Style DNA Engine (`style-dna-v1.0.0`)**: Automated full-image characterization across 9 visual dimensions (D1..D9: color energy, color diversity, contrast, warmth, visual complexity, structural order, rhythm repetition, focal strength, form language).
- **Explicit Multimodal Preference Assessment (`preference-confidence-v1`, `importance-v1`)**: 6-question text assessment, 6-pair visual stimulus assessment, and explicit 4-priority user importance profile review.
- **Explainable Visual Style Match Engine (`visual-style-match-v1`)**: Deterministic weighted similarity scoring against catalog carpets with categorical match labels (`VERY_STRONG`, `STRONG`, `MODERATE`, `LIMITED`, `LOW`) and 9D dimension-level breakdowns.
- **Curated Motif Story Knowledge & Catalog Associations (`motif-story-knowledge-v1`, `carpet-catalog-curation-v1`)**: 8 narrative themes (N1..N8), verified claim source citations (`ACADEMIC_PUBLICATION`, `MUSEUM_CATALOG`, `EXPERT_MONOGRAPH`), and carpet catalog story snapshot associations.
- **Explainable Narrative Affinity Engine (`narrative-affinity-v1`)**: User narrative profile (N1..N8 interest levels) matched against carpet motif stories with categorical affinity labels (`VERY_STRONG`, `STRONG`, `MODERATE`, `LIMITED`, `NOT_AVAILABLE`) and evidence attribution.
- **Verified Historical Reference Collection (`historical-reference-v1`)**: 12 verified museum/archive reference items (V&A, Met, Louvre, TIEM, Al-Sabah) with primary source citations and provenance status (`VERIFIED_HISTORICAL`, `ATTRIBUTED`, `CONTESTED`).
- **Explainable Historical Connection Engine (`historical-connection-v1`)**: Pairwise visual proximity matching with categorical proximity labels (`VERY_CLOSE`, `CLOSE`, `MODERATE`, `LIMITED`), 9D similarity breakdowns, and historical reference metadata.
- **Frontend Product Experience (`frontend-experience-v1`)**: Production Next.js 15 App Router experience featuring interactive preference assessment, Style DNA radar visualization, catalog browsing, detailed carpet pages with Visual Style Match, Narrative Affinity, and Historical Connections.
- **Validation, Calibration & E2E Benchmark (`validation-benchmark-v1`, `release-contract-v1`)**: 57-check automated validation benchmark verifying mathematical properties, contract invariants, idempotency, and non-regression across all engines.
- **Production Hardening & Operational Readiness (`production-readiness-v1`)**: Fail-fast production config validation, PostgreSQL pool hardening, `/health/live` and `/health/ready` probes, single-line JSON logging with correlation IDs (`X-Request-ID`), bounded rate limiting, S3/MinIO storage factory, Docker compose setup, and backup tooling.
- **Release Candidate & Final Acceptance (`v1.0.0-rc.1`)**: Complete release package, machine-readable manifests, OpenAPI schema snapshot, and final acceptance documentation.
