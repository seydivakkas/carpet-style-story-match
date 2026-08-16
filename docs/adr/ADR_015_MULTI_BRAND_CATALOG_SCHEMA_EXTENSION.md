# ADR 015 — Multi-Brand Catalog Brand Registry Schema Extension

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

- **Status**: Formally Accepted
- **Date**: 2026-08-16
- **Context**: V2-01 Multi-Brand Carpet Catalog Architecture

## 1. Problem Statement
The original Core v1 catalog schema assumed a single manufacturer (`manufacturer: Optional[str]`) stored as a free-text string column directly on `carpets`. To support verified multi-brand catalog architecture, manufacturer legal entities must be cleanly separated from consumer branding (`brand_name`), and source metadata (`brand_key`, `brand_website`, `logo_url`, `is_verified`, `parser_module`) must be tracked with strict data provenance.

## 2. Decision & Minimal Schema Design
We created `ManufacturerBrandModel` table (`manufacturer_brands`) and added `brand_id` foreign key column on `carpets` referencing `manufacturer_brands.id` with `ondelete='SET NULL'`:

```sql
CREATE TABLE manufacturer_brands (
    id UUID NOT NULL PRIMARY KEY,
    brand_key VARCHAR(100) NOT NULL UNIQUE,
    brand_name VARCHAR(255) NOT NULL,
    brand_website TEXT,
    logo_url TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    parser_module VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE carpets ADD COLUMN brand_id UUID REFERENCES manufacturer_brands(id) ON DELETE SET NULL;
```

## 3. Minimality & Backward Compatibility
- `CarpetModel` is reused directly without creating parallel tables (no `MultiBrandCarpetModel`).
- `brand_id` is nullable (`Optional[UUID]`), preserving compatibility with existing 232 Merinos rows.
- Existing SKUs and business identifiers remain untouched.
- `brand_id` was backfilled on all 232 catalog carpets pointing to Merinos brand record (`8c2d9316-1c96-4cb8-8b9d-bcb710417cb4`).

## 4. Product Identity Semantics
Product identity is provider-scoped: `provider_key + brand_key + official_sku`. Same SKU across different brands is permitted as distinct products. Same `provider_key + brand_key + official_sku` is rejected as duplicate.

## 5. Rollback Considerations
If downgraded, Alembic migration 015 drops constraint `fk_carpets_brand_id`, column `brand_id` from `carpets`, and table `manufacturer_brands` using SQLite batch mode support without affecting non-brand columns.
