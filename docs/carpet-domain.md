# Carpet Domain Specification

## 1. Domain Purpose

The **Carpet Aggregate** represents a carpet item record within the catalog or workspace. It stores core item metadata, physical dimensions, origin semantics, and catalog classifications.

> **CRITICAL BOUNDARY INVARIANT**:
> `Carpet` is strictly item metadata. It does NOT store 9D Style DNA vectors, preference vectors, match scores, personality evaluations, or AI confidence ratings. Future tasks will connect `Carpet` to distinct entities such as `CarpetStyleProfile` or `MotifStory`.

---

## 2. Field Definitions

| Field Name | Type | Required | Constraints / Description |
|---|---|---|---|
| `id` | UUID (v4) | Yes | Primary Key, server-generated |
| `sku` | String | No | Unique if present. Empty/whitespace strings normalize to `NULL`. |
| `name` | String | Yes | Non-empty string, whitespace trimmed. |
| `description` | Text | No | Free-form item description. |
| `manufacturer` | String | No | Producer/brand metadata (e.g., "Merinos"). |
| `collection` | String | No | Collection/line identifier. |
| `width_cm` | Float | No | Positive numeric (`> 0.0`). |
| `height_cm` | Float | No | Positive numeric (`> 0.0`). |
| `material` | String | No | Fiber composition (e.g., "Wool", "Silk", "Cotton"). |
| `style_label` | String | No | Catalog style taxonomy (e.g., "traditional", "modern", "transitional"). |
| `source_type` | Enum | Yes | Origin classification (`CATALOG`, `USER_UPLOAD`, `HISTORICAL`, `MANUAL`). Default: `CATALOG`. |
| `source_reference` | String | No | External SKU, museum accession ID, or reference source key. |
| `is_active` | Boolean | Yes | Catalog availability status. Default: `true`. |
| `created_at` | DateTime | Yes | UTC timestamp (timezone aware), set on creation. |
| `updated_at` | DateTime | Yes | UTC timestamp (timezone aware), updated on modification. |

---

## 3. Style Label vs Style DNA

- **`style_label`**: Textual metadata assigned by manufacturers or catalog editors (e.g., "vintage", "anatolian").
- **`Style DNA`**: The canonical 9D vector (D1 `color_energy` ... D9 `form_language`) computed algorithmically from carpet imagery.
- **Invariant**: `style_label` MUST NEVER be used as a substitute for 9D Style DNA.

---

## 4. API Endpoints

- `POST /api/v1/carpets`: Creates a new carpet record (201 Created).
- `GET /api/v1/carpets`: Lists carpets with pagination (`limit`, `offset`) and optional metadata filters (`manufacturer`, `collection`, `style_label`, `is_active`).
- `GET /api/v1/carpets/{carpet_id}`: Retrieves a single carpet by UUID (200 OK or 404 Not Found).
- `PATCH /api/v1/carpets/{carpet_id}`: Updates specified carpet fields partially (200 OK, 404 Not Found, or 409 Conflict).
- `DELETE /api/v1/carpets/{carpet_id}`: Deletes a carpet record (204 No Content or 404 Not Found).

---

## 5. Database Constraints

- `carpets_pkey`: PRIMARY KEY (`id`)
- `uq_carpets_sku`: UNIQUE (`sku`) WHERE `sku IS NOT NULL`
- `ck_carpets_name_not_empty`: CHECK (`length(trim(name)) > 0`)
- `ck_carpets_width_positive`: CHECK (`width_cm IS NULL OR width_cm > 0`)
- `ck_carpets_height_positive`: CHECK (`height_cm IS NULL OR height_cm > 0`)

---

## 6. Future Entity Relations

```text
Carpet (Aggregate Root)
├── CarpetImage          (1:N - Future Task 02)
├── CarpetStyleProfile   (1:1 - Future Task 03)
├── MotifStory           (M:N - Future Task 06)
└── HistoricalLink       (M:N - Future Task 07)
```
