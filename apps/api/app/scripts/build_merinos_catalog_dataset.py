"""Builder script to acquire official Merinos public catalog metadata and build activation datasets."""
import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Set, Optional

from app.domain.carpet_catalog.merinos_parser import (
    parse_collection_page,
    parse_product_page,
    normalize_sku,
)
from app.domain.carpet_catalog.schemas import CatalogImportDataset

HEADERS = {
    "User-Agent": "CarpetStyleStoryMatch/1.0.0-rc.1 DataAcquisition/1.0 (+http://localhost)"
}
BASE_URL = "https://www.merinos.com.tr"

# Official Merinos collection menu items from https://www.merinos.com.tr/koleksiyonlarimiz
OFFICIAL_MERINOS_COLLECTIONS = [
    "Elegance",
    "Arden",
    "Vega",
    "Octavia",
    "Ritim",
    "Havana",
    "Premium",
    "Lion",
    "Toronto",
    "Diyez",
    "Launge",
    "Therapy",
    "Rodin",
    "Recycle",
    "Valeria",
]


def get_repo_root() -> str:
    """Return the absolute path of the repository root."""
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(os.path.dirname(current_file), "..", "..", "..", ".."))


def fetch_url(url: str, timeout: int = 10, delay_sec: float = 0.5) -> str:
    """Fetch URL contents with deterministic User-Agent, timeout, and conservative delay."""
    time.sleep(delay_sec)
    parsed = urllib.parse.urlparse(url)
    quoted_path = urllib.parse.quote(parsed.path)
    safe_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, quoted_path, parsed.params, parsed.query, parsed.fragment))

    req = urllib.request.Request(safe_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def discover_collections(specified_collections: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Get specified collections or official collection list."""
    target_names = specified_collections if specified_collections else OFFICIAL_MERINOS_COLLECTIONS
    collections = []
    for name in target_names:
        clean_name = name.strip()
        collections.append({
            "name": clean_name,
            "url": f"{BASE_URL}/{clean_name}"
        })
    return collections


def process_acquisition(collections: List[Dict[str, str]]) -> Dict[str, Any]:
    """Process collections, extract product URLs, fetch product detail metadata, deduplicate by SKU."""
    retrieved_at = datetime.now(timezone.utc).isoformat()

    discovered_links: List[str] = []
    seen_links: Set[str] = set()

    print("[1/4] Extracting product links from official Merinos collections...")
    for col in collections:
        col_url = col["url"]
        col_name = col["name"]
        print(f"  Processing collection: {col_name} ({col_url})")
        try:
            html = fetch_url(col_url)
            parsed_col = parse_collection_page(html, col_url)
            for link in parsed_col["product_links"]:
                if link not in seen_links:
                    seen_links.add(link)
                    discovered_links.append(link)
        except Exception as e:
            print(f"    Failed to fetch collection {col_name}: {e}", file=sys.stderr)

    print(f"  Total unique product links discovered: {len(discovered_links)}")

    print("[2/4] Fetching product metadata & normalizing SKUs...")
    products_by_sku: Dict[str, Dict[str, Any]] = {}
    duplicate_sku_count = 0
    invalid_sku_count = 0
    sku_conflicts = []

    for idx, prod_url in enumerate(discovered_links, 1):
        print(f"  [{idx}/{len(discovered_links)}] Fetching product: {prod_url}")
        try:
            html = fetch_url(prod_url)
            prod_data = parse_product_page(html, prod_url)

            sku = prod_data["sku"]
            if not sku:
                print(f"    WARNING: Product at {prod_url} has invalid/empty SKU", file=sys.stderr)
                invalid_sku_count += 1
                continue

            if sku in products_by_sku:
                duplicate_sku_count += 1
                existing = products_by_sku[sku]
                if existing["name"] != prod_data["name"] and existing["collection"] != prod_data["collection"]:
                    print(f"    NOTICE: Duplicate SKU '{sku}' found in multiple collections ({existing['collection']} vs {prod_data['collection']})")
                    sku_conflicts.append({
                        "sku": sku,
                        "primary_collection": existing["collection"],
                        "secondary_collection": prod_data["collection"]
                    })
            else:
                products_by_sku[sku] = prod_data

        except Exception as e:
            print(f"    Failed to process product {prod_url}: {e}", file=sys.stderr)

    unique_products = list(products_by_sku.values())
    print(f"  Acquired {len(unique_products)} unique official product records.")

    source_dataset = {
        "dataset_type": "merinos-public-catalog-source",
        "source": "official-public-site",
        "retrieved_at": retrieved_at,
        "collections_processed": [c["name"] for c in collections],
        "products": unique_products
    }

    curation_carpets = []
    for p in unique_products:
        curation_carpets.append({
            "sku": p["sku"],
            "name": p["name"],
            "description": None,
            "manufacturer": p["manufacturer"],
            "collection": p["collection"],
            "width_cm": None,
            "height_cm": None,
            "material": None,
            "style_label": None,
            "source_reference": p["source_url"],
            "is_active": True,
            "motifs": []
        })

    curation_dataset = {
        "schema_version": "carpet-catalog-curation-v1",
        "carpets": curation_carpets
    }

    # Validate against CatalogImportDataset schema
    CatalogImportDataset.model_validate(curation_dataset)

    report = {
        "retrieved_at": retrieved_at,
        "collection_count": len(collections),
        "discovered_product_links": len(discovered_links),
        "unique_sku_count": len(unique_products),
        "duplicate_sku_count": duplicate_sku_count,
        "invalid_sku_count": invalid_sku_count,
        "sku_conflicts_count": len(sku_conflicts),
        "products_ready_for_import": len(curation_carpets),
        "products_blocked": 0,
        "dimension_contract_status": "DIMENSIONS_OPTIONAL_NULL_STORED"
    }

    return {
        "source_dataset": source_dataset,
        "curation_dataset": curation_dataset,
        "report": report
    }


def main():
    repo_root = get_repo_root()
    default_source_path = os.path.join(repo_root, "data", "activation", "merinos", "merinos-catalog-source.json")
    default_curation_path = os.path.join(repo_root, "data", "activation", "merinos", "merinos-catalog-curation.json")
    default_report_path = os.path.join(repo_root, "data", "activation", "merinos", "activation-report.json")

    parser = argparse.ArgumentParser(description="Build official Merinos catalog activation datasets.")
    parser.add_argument("--output-source", default=default_source_path, help="Path for source provenance dataset")
    parser.add_argument("--output-curation", default=default_curation_path, help="Path for curation import dataset")
    parser.add_argument("--report", default=default_report_path, help="Path for quality report")
    parser.add_argument("--collection", action="append", help="Specify specific collection(s) to fetch (can pass multiple times for pilot)")

    args = parser.parse_args()

    print("=== MERINOS CATALOG DATASET BUILDER ===")
    collections = discover_collections(args.collection)
    
    results = process_acquisition(collections)

    print("[3/4] Writing datasets to output paths...")
    os.makedirs(os.path.dirname(os.path.abspath(args.output_source)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.output_curation)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)

    with open(args.output_source, "w", encoding="utf-8") as f:
        json.dump(results["source_dataset"], f, ensure_ascii=False, indent=2)
    print(f"  Source dataset saved: {args.output_source}")

    with open(args.output_curation, "w", encoding="utf-8") as f:
        json.dump(results["curation_dataset"], f, ensure_ascii=False, indent=2)
    print(f"  Curation dataset saved: {args.output_curation}")

    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(results["report"], f, ensure_ascii=False, indent=2)
    print(f"  Quality report saved: {args.report}")

    print("\n[SUCCESS] Datasets generated and validated successfully.")


if __name__ == "__main__":
    main()
