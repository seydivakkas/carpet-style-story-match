# Carpet Catalog v1 Spec

## Overview

Carpet Catalog manages product records that are commercially or curatedly available in the repository domain (`source_type == CATALOG`). Catalog carpets inherit all core carpet domain capabilities while introducing strict business key constraints (`sku`), evidence-backed motif associations, and curated motif story associations.

---

## Technical Invariants

1. **No Second Carpet Entity**: Re-uses `CarpetModel` where `source_type == CATALOG`. No duplicate product model.
2. **SKU Business Key**: Every catalog carpet MUST have a non-empty, trimmed, indexed, unique `sku`.
3. **No Uniqueness Conflicts**: Catalog SKUs cannot collide with other catalog carpets or non-catalog carpets (`source_type != CATALOG`).
4. **Derived Style DNA Readiness**: Read operations dynamically derive `StyleDnaReadinessEnum` (`NO_PRIMARY_IMAGE`, `STYLE_DNA_MISSING`, `STYLE_DNA_FAILED`, `STYLE_DNA_PARTIAL`, `STYLE_DNA_COMPLETE`) without side effects.
5. **Read-Only Public API**: All public API endpoints (`/api/v1/catalog/...`) are read-only. Data ingestion and curation updates are handled via internal CLI script (`import_carpet_catalog.py`).

---

## API Endpoints

- `GET /api/v1/catalog/carpets?limit=20&offset=0&manufacturer=...&collection=...&material=...&style_label=...`
- `GET /api/v1/catalog/carpets/{id_or_sku}`
- `GET /api/v1/catalog/carpets/{id_or_sku}/motifs`
- `GET /api/v1/catalog/carpets/{id_or_sku}/story-associations`

---

## CLI Ingestion

```bash
python -m app.scripts.import_carpet_catalog path/to/dataset.json [--dry-run]
```
