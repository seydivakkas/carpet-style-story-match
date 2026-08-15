# External Carpet Dataset Source Matrix

This matrix defines the governance, default roles, catalog eligibility, and historical candidacy rules for external carpet datasets.

| Dataset Key | Provider Type | Default Role | Catalog Eligible? | Historical Candidate? | Research Use | License State | Provenance Risk | Key Governance Rules |
|-------------|---------------|--------------|-------------------|-----------------------|--------------|---------------|-----------------|----------------------|
| `official-merinos-catalog` | `OFFICIAL_MANUFACTURER` | `CATALOG_CANDIDATE` | **ELIGIBLE** | `INELIGIBLE` | Commercial Catalog | Verified Official | Low | Verified manufacturer, official SKU required |
| `generic-persian-rugs` | `KAGGLE` | `RESEARCH_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Feature Research | Unverified | High | Web scrape without official SKU; cannot enter /catalog |
| `iranian-patterns` | `ACADEMIC_DATASET` | `RESEARCH_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Pattern Classification | Verified CC-BY-4.0 | Low | Namespaced source labels; curated mapping required |
| `safavid-carpets-originals` | `MUSEUM` / `ACADEMIC` | `RESEARCH_ONLY` | `INELIGIBLE` | **REVIEW / ELIGIBLE** (per-image) | Heritage Curation | Verified CC0-1.0 | Low | Default RESEARCH_ONLY; HISTORICAL_CANDIDATE only when per-image museum object ID & URL are verified |
| `safavid-carpets-augmentations` | `ACADEMIC_DATASET` | `BENCHMARK_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Robustness Benchmark | Verified CC-BY-4.0 | Low | Augmented data strictly blocked from production promotion |
| `rug-construction-detection` | `ROBOFLOW` | `RESEARCH_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Construction Analysis | Verified CC-BY-4.0 | Medium | Technical weave detection; no catalog promotion |
| `met-open-access-carpets` | `MUSEUM` | `HISTORICAL_CANDIDATE` | `INELIGIBLE` | **ELIGIBLE** | Heritage Reference | Verified CC0-1.0 | Low | Stable MET object ID & public domain rights verified |
