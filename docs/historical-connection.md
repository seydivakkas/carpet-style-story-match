# Explainable Historical Connection Engine v1 — Technical Specification & Architecture

## Overview

The **Explainable Historical Connection Engine v1** (`historical-connection-v1`) provides deterministic, unweighted, 9-dimensional Style DNA similarity comparison between catalog carpets (target) and verified museum/archival historical reference carpets (reference).

The engine is designed with strict domain boundaries and truthful explainability rules:
- **Style Similarity Only**: Evaluates visual similarity based strictly on standard Style DNA 9 dimensions.
- **No Probability / No Historical Attribution**: Does NOT compute authenticity probabilities or claim direct historical provenance/attribution.
- **Strict Input Validation**: Rejects target carpets of `source_type = HISTORICAL`.
- **Truthful Coverage**: Requires at least 6 comparable dimensions for a valid similarity score. With 6–8 comparable dimensions, status is `PARTIAL`. Below 6 comparable dimensions, status is `NOT_AVAILABLE`.
- **Standardized Disclaimer**: Every response includes an explicit Turkish disclaimer explaining that visual similarity does not constitute historical attribution or authentication.

---

## Technical Architecture & Flow

```mermaid
graph TD
    Client[API Client / UI] -->|POST /api/v1/historical-connections| Router[FastAPI Historical Connection Router]
    Router --> Service[HistoricalConnectionService]
    Service --> Repo[HistoricalConnectionRepository]
    Service --> Engine[HistoricalConnectionEngine (Pure)]
    Service --> ExplBuilder[HistoricalConnectionExplanationBuilder (Pure)]
    Repo --> DB[(PostgreSQL Database)]
```

---

## Data Model & DB Schema

### Tables

1. `carpet_historical_connections`
   - `id` (UUID, PK)
   - `target_carpet_id` (FK -> `carpets.id`)
   - `target_style_profile_id` (FK -> `carpet_style_profiles.id`)
   - `historical_carpet_id` (FK -> `carpets.id`)
   - `historical_reference_metadata_id` (FK -> `carpet_historical_reference_metadata.id`)
   - `historical_style_profile_id` (FK -> `carpet_style_profiles.id`)
   - `connection_version` (`historical-connection-v1`)
   - `status` (`COMPLETE` | `PARTIAL` | `NOT_AVAILABLE`)
   - `not_available_reason` (String)
   - `style_similarity` (Float, 0.0 - 1.0)
   - `connection_level` (`VERY_CLOSE` | `CLOSE` | `MODERATE` | `LIMITED`)
   - `comparable_dimension_count` (Int, 0 - 9)
   - `dimension_coverage` (Float, 0.0 - 1.0)
   - `created_at` (Timestamp)

2. `carpet_historical_connection_dimensions`
   - `id` (UUID, PK)
   - `historical_connection_id` (FK -> `carpet_historical_connections.id`)
   - `dimension_key` (String)
   - `target_value` (Float)
   - `target_status` (String)
   - `target_confidence` (Float)
   - `reference_value` (Float)
   - `reference_status` (String)
   - `reference_confidence` (Float)
   - `difference` (Float)
   - `similarity` (Float)
   - `comparable` (Boolean)

---

## Similarity Metrics & Rules

### Pure Difference Formula
For each dimension $d \in \{\text{D1} \dots \text{D9}\}$:
$$\Delta_d = |v_{\text{target}, d} - v_{\text{reference}, d}|$$
$$\text{Sim}_d = 1.0 - \Delta_d$$

### Overall Style Similarity
$$\text{StyleSimilarity} = \frac{\sum_{d \in C} \text{Sim}_d}{|C|}$$
where $C$ is the set of comparable dimensions.

### Connection Levels
- $\ge 0.90 \implies$ **`VERY_CLOSE`** ("Çok Yakın Görsel Tarihsel Bağlantı")
- $\ge 0.75 \implies$ **`CLOSE`** ("Yakın Görsel Tarihsel Bağlantı")
- $\ge 0.60 \implies$ **`MODERATE`** ("Orta Düzey Görsel Tarihsel Bağlantı")
- $< 0.60 \implies$ **`LIMITED`** ("Sınırlı Görsel Tarihsel Bağlantı")

---

## API Endpoints

- `POST /api/v1/historical-connections`: Evaluates and persists historical connection between target profile and historical reference.
- `GET /api/v1/historical-connections/{id}`: Retrieves detailed connection result with full explanation, reference context, and dimension snapshots.
- `GET /api/v1/historical-connections`: Lists connection results with filtering and pagination.
- `GET /api/v1/meta/historical-connections`: Returns metadata, threshold rules, and connection version information.
