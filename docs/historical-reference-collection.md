# Verified Historical Reference Collection v1

> ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
> Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
> Bu yazılım ve ilgili tüm dosyalar yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.

---

## 1. Architectural Role & Invariants

The **Verified Historical Reference Collection v1** (`historical-reference-v1`, curation schema `historical-reference-curation-v1`) introduces a source-backed knowledge repository of historical carpet reference objects from accredited museums, archives, and institutional collections.

### Core Non-Negotiable Invariants:
1. `HISTORICAL REFERENCE != HISTORICAL AUTHENTICATION OF USER/CATALOG CARPET`: Storing a historical reference carpet object does not imply commercial carpets or user-uploaded carpets are historical or authentic.
2. `VISUAL SIMILARITY != ATTRIBUTION`: Visual similarity measurements (Style DNA) or motif matches never constitute historical attribution or physical provenance.
3. `SOURCE-REPORTED CULTURE != SYSTEM-INFERRED CULTURE`: The system stores culture labels exactly as reported by holding institutions without automatic normalization or ML inference.
4. `SOURCE-REPORTED PERIOD != SYSTEM-INFERRED PERIOD`: Period and date strings are preserved strictly as source-reported metadata.
5. `REFERENCE COLLECTION != CLASSIFIER`: The reference collection is a curated knowledge base, not a training classifier.
6. `UNKNOWN REMAINS UNKNOWN`: If an institution leaves culture, period, date, or geography blank, it remains `NULL`. No default values or fallback guesses are inserted.

---

## 2. Entity Architecture & CarpetModel Reuse

Historical reference records reuse `CarpetModel` where `source_type == CarpetSourceType.HISTORICAL`.

```
CarpetModel (source_type = HISTORICAL)
    │
    ├── 1:1 ── HistoricalReferenceMetadataModel
    │             ├── reference_key (unique, human-readable)
    │             ├── institution_name & object_identifier (unique composite)
    │             ├── object_title, culture, period, dynasty_or_tradition
    │             ├── date_display, date_start_year, date_end_year
    │             ├── geography, medium, dimensions_text, department
    │             ├── credit_line, object_url, source_image_url
    │             └── rights_statement, open_access, curation_note
    │
    └── 1:N ── HistoricalReferenceSourceModel
                  ├── source_role (PRIMARY_OBJECT_RECORD | SUPPORTING_REFERENCE)
                  └── FK ── CuratedSourceModel (curated_sources)
```

### Source Link Rules:
- **PRIMARY_OBJECT_RECORD**: Exactly 1 per historical reference. The linked `CuratedSourceModel` MUST have `source_type` equal to `MUSEUM_OBJECT` or `ARCHIVE_RECORD`.
- **SUPPORTING_REFERENCE**: 0..N per historical reference. Links to academic books, articles, or catalog publications providing secondary analysis or context.

---

## 3. Curation Importer & CLI

Importing historical reference datasets is performed via `HistoricalReferenceImporter` or the CLI script:

```bash
python -m app.scripts.import_historical_references dataset.json [--dry-run]
```

### Import Validation Rules:
1. `schema_version`: Must equal `historical-reference-curation-v1`.
2. Required identity fields: `reference_key`, `institution_name`, `object_identifier`, `object_title`.
3. Date range: If both `date_start_year` and `date_end_year` are specified, `date_start_year <= date_end_year`.
4. Idempotency: Re-importing exact identical records skips without side effects.
5. Conflicts: Re-importing an existing `reference_key` with altered metadata raises `HistoricalReferenceConflictError`. Re-using an existing `(institution_name, object_identifier)` under a different `reference_key` raises `HistoricalReferenceObjectConflictError`.

---

## 4. Side-Effect-Free Public APIs

All public endpoints are strictly read-only:

- `GET /api/v1/historical-references`
  - Paginated list with filtering by `institution`, `culture`, `period`, `dynasty_or_tradition`, `department`.
  - Deterministic ordering: `institution_name ASC`, `object_identifier ASC`, `reference_key ASC`.
- `GET /api/v1/historical-references/{id_or_reference_key}`
  - Detailed object record with `primary_source`, `supporting_sources` (sorted by `source_key`), primary image metadata, and `style_dna_readiness`.
- `GET /api/v1/meta/historical-references`
  - Curation schema version (`historical-reference-curation-v1`), API version (`historical-reference-v1`), enum values.

---

## 5. Style DNA Readiness Derivation

`style_dna_readiness` is computed dynamically side-effect-free using `derive_style_dna_readiness`:

| State | Condition |
|-------|-----------|
| `NO_PRIMARY_IMAGE` | No primary `CarpetImage` linked to reference carpet |
| `STYLE_DNA_MISSING` | Primary image exists, but no `style-dna-v1.0.0` profile |
| `STYLE_DNA_FAILED` | Latest profile status is `FAILED` |
| `STYLE_DNA_PARTIAL` | Latest profile status is `PARTIAL` |
| `STYLE_DNA_COMPLETE` | Latest profile status is `COMPLETE` |
