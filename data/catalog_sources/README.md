# Catalog Source Registry & Official Source Policy

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## Overview
This directory manages provenanced catalog source registries for multi-brand carpet data integration.

## Key Principles & Policies

1. **Official Source Policy**
   - Production product activation is restricted strictly to official manufacturer sites, official brand domains, and official corporate catalogs.
   - E-commerce marketplaces (Trendyol, Hepsiburada, Amazon), general rug stores, social media platforms, or unverified web scrapes must **NEVER** serve as canonical product sources.

2. **Manufacturer != Brand Semantics**
   - Brand name and legal manufacturer are stored as distinct entities.
   - `manufacturer` remains `null` unless explicitly documented by official corporate sources.

3. **URL_ONLY Image Policy**
   - Newly discovered brand product image references use `URL_ONLY` policy by default.
   - Local storage activation and Style DNA processing are restricted to authorized local primary images.

4. **Idempotent Product Identity**
   - Products are uniquely identified by `provider_key + brand_key + official_sku`.
