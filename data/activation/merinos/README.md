# Merinos Catalog Activation Dataset v1 (Post-v1 A1)

## Data Origin & Rights Notice

- **Origin**: All product metadata in this directory originates strictly from official, publicly accessible product pages on [Merinos Official Website](https://www.merinos.com.tr/).
- **Public Scraped Data Only**: No private dealer portals, authenticated APIs, or restricted endpoints were accessed.
- **Imagery Policy (A1 Scope)**: Product image binaries are **NOT** downloaded or stored in A1. Image URLs are preserved as sidecar provenance metadata for future A2 image activation.
- **Copyrighted Text Policy**: Full copyrighted page HTML and long descriptions are **NOT** stored. Only factual, non-copyrightable catalog metadata (SKU, title, collection, available size specifications, product URLs) is retained.
- **Provenance**: `source_reference` (Product URL) and SHA-256 `source_hash` are attached to each product record for provenance tracking and source drift detection.
- **Legal Compliance**: Usage of this metadata must strictly comply with applicable intellectual property and terms of use governing Merinos catalog data.

---

## File Structure

- `merinos-catalog-source.json`: Raw acquisition provenance dataset containing sidecar metadata (`available_sizes`, `primary_image_url`, `source_hash`).
- `merinos-catalog-curation.json`: Formatted import dataset adhering strictly to `carpet-catalog-curation-v1` schema.
- `activation-report.json`: Data quality and acquisition summary report.
