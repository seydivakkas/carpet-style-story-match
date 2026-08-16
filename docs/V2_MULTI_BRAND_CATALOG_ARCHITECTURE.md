# V2 Multi-Brand Catalog Architecture

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## Architecture Principles

1. **Reused Core Models**: The core `CarpetModel` database table is reused without schema pollution, linked to `ManufacturerBrandModel` via `brand_id` foreign key.
2. **Provider Adapter Abstraction**: All brand adapters inherit from `CatalogSourceAdapter` and enforce deterministic SHA-256 source hashing over normalized product metadata.
3. **Official Source Policy**: Production product records must strictly originate from verified manufacturer or brand domains. E-commerce marketplaces are forbidden as canonical sources.
4. **Manufacturer != Brand**: Legal producer (`manufacturer`) is distinct from consumer branding (`brand_name`).
5. **URL_ONLY Image Policy**: New provider image references default to `URL_ONLY` unless local storage authorization is explicitly granted. Style DNA extraction only runs on authorized local primary images.
6. **Canonical Image Resolver**: Frontend applications utilize `getCarpetPrimaryImageUrl(carpet)` pointing to `/api/v1/carpets/{id}/images/{image_id}/content`.
