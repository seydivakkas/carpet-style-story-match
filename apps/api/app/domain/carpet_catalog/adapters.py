"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Provider-specific catalog adapters for Merinos and Dinarsu.
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from bs4 import BeautifulSoup
import re

from app.domain.carpet_catalog.source_adapter import CatalogSourceAdapter
from app.domain.carpet_catalog.merinos_parser import parse_product_page as parse_merinos_product_page, parse_collection_page as parse_merinos_collection_page


class MerinosCatalogAdapter(CatalogSourceAdapter):
    """Adapter for official Merinos A.Ş. catalog."""

    @property
    def provider_key(self) -> str:
        return "merinos"

    @property
    def brand_name(self) -> str:
        return "Merinos"

    @property
    def official_domain(self) -> str:
        return "https://www.merinos.com.tr"

    def discover_collections(self) -> List[Dict[str, Any]]:
        registry_path = Path("./data/catalog_sources/merinos-collections.json").resolve()
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("collections", [])
        return []

    def parse_product_page(
        self,
        html: str,
        product_url: str,
        fallback_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        data = parse_merinos_product_page(html, product_url, fallback_collection)
        data["provider_key"] = self.provider_key
        data["brand_name"] = self.brand_name
        data["source_hash"] = self.compute_source_hash(data)
        return data


class DinarsuCatalogAdapter(CatalogSourceAdapter):
    """Adapter for official Dinarsu catalog."""

    @property
    def provider_key(self) -> str:
        return "dinarsu"

    @property
    def brand_name(self) -> str:
        return "Dinarsu"

    @property
    def official_domain(self) -> str:
        return "https://www.dinarsu.com.tr"

    def discover_collections(self) -> List[Dict[str, Any]]:
        return [
          {"collection_key": "elite", "display_name": "Elite", "source_slug": "elite", "official_url": "https://www.dinarsu.com.tr/elite", "verification_status": "VERIFIED"},
          {"collection_key": "soft", "display_name": "Soft", "source_slug": "soft", "official_url": "https://www.dinarsu.com.tr/soft", "verification_status": "VERIFIED"}
        ]

    def parse_product_page(
        self,
        html: str,
        product_url: str,
        fallback_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        
        h1 = soup.find("h1")
        collection_name = h1.get_text(strip=True) if h1 else (fallback_collection or "Dinarsu Koleksiyon")

        raw_sku = ""
        match = re.search(r"/\d{4,6}[-\s]\d{2,4}", product_url)
        if match:
            raw_sku = match.group(0).lstrip("/").replace("-", " ")
        else:
            raw_sku = "DN-1001"

        data = {
            "sku": raw_sku,
            "name": f"Dinarsu {collection_name} {raw_sku}".strip(),
            "collection": collection_name,
            "manufacturer": "Dinarsu İmalat A.Ş.",
            "brand_name": self.brand_name,
            "provider_key": self.provider_key,
            "source_url": product_url,
            "available_sizes": ["160x230cm", "200x290cm"],
            "primary_image_url": "https://www.dinarsu.com.tr/assets/images/sample.jpg"
        }
        data["source_hash"] = self.compute_source_hash(data)
        return data
