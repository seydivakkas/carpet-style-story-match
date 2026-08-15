# External Carpet Dataset Registry & Intake System

This directory contains metadata registries, intake manifests, and dataset governance configuration for external carpet image corpora (Kaggle, Roboflow, Museum Open Access, Academic datasets, GitHub, and Internal collections).

---

## Directory Structure

```
data/external_datasets/
├── registry.json             # Central registry of external datasets
├── label-mappings.json       # Curated mapping from source labels to canonical taxonomy
├── manifests/                # Per-dataset .jsonl manifest files
├── raw/                      # Ignored directory for raw local image corpora
├── cache/                    # Ignored directory for temporary cache
└── reports/                  # Quality and classification reports per dataset
```

---

## Core Invariants

1. **DATASET IMAGE != CATALOG PRODUCT**: External research datasets do NOT automatically enter production catalog (`CarpetModel(source_type=CATALOG)`).
2. **NO VISUAL CATALOG CLASSIFICATION**: Catalog eligibility is derived exclusively from verified manufacturer provenance and official SKU, never from pixel similarity or CLIP heuristics.
3. **OFFICIAL SKU REQUIRED**: Catalog promotion strictly requires a non-empty official manufacturer SKU.
4. **NO SYNTHETIC/AUGMENTED PROMOTION**: Augmented or synthetic images are classified as `BENCHMARK_ONLY` and cannot enter production catalog or historical reference tables.
5. **LICENSE GATE**: `license_verified: false` blocks automatic promotion.

---

## Roles & Eligibility

| Classified Role | Catalog Eligibility | Historical Eligibility | Description |
|-----------------|---------------------|------------------------|-------------|
| `CATALOG_CANDIDATE` | `ELIGIBLE` / `REVIEW_REQUIRED` | `INELIGIBLE` | Verified commercial product from official manufacturer with official SKU |
| `HISTORICAL_CANDIDATE` | `INELIGIBLE` | `ELIGIBLE` / `REVIEW_REQUIRED` | Verified museum/archive object with stable accession ID |
| `RESEARCH_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Academic, Kaggle, or research datasets for feature extraction & distribution study |
| `BENCHMARK_ONLY` | `INELIGIBLE` | `INELIGIBLE` | Augmented or synthetic images used solely for robustness evaluation |
| `QUARANTINE` | `INELIGIBLE` | `INELIGIBLE` | Unverified origin, missing required provenance, or untrusted metadata |

---

## CLI Usage Example

```bash
python -m app.scripts.inspect_external_carpet_dataset \
  --dataset-key iranian-patterns \
  --input-dir data/external_datasets/raw/iranian-patterns \
  --provider-type KAGGLE \
  --source-url "https://www.kaggle.com/datasets/..." \
  --license-name "CC-BY-4.0" \
  --license-verified \
  --output-manifest data/external_datasets/manifests/iranian-patterns.jsonl \
  --output-report data/external_datasets/reports/iranian-patterns-report.json
```
