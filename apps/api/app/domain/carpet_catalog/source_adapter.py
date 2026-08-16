"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Abstract Base Class for Catalog Source Adapters.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import hashlib
import json


class CatalogSourceAdapter(ABC):
    """Abstract contract for provider-specific catalog source adapters."""

    @property
    @abstractmethod
    def provider_key(self) -> str:
        """Return provider key e.g. 'merinos', 'dinarsu'."""
        pass

    @property
    @abstractmethod
    def brand_name(self) -> str:
        """Return display brand name."""
        pass

    @property
    @abstractmethod
    def official_domain(self) -> str:
        """Return official website domain."""
        pass

    @abstractmethod
    def discover_collections(self) -> List[Dict[str, Any]]:
        """Discover collection metadata and URLs from official registry or site."""
        pass

    @abstractmethod
    def parse_product_page(
        self,
        html: str,
        product_url: str,
        fallback_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse product page HTML into normalized product record."""
        pass

    def compute_source_hash(self, product_data: Dict[str, Any]) -> str:
        """Compute deterministic SHA-256 over normalized product source record."""
        hash_dict = {
            "provider_key": self.provider_key,
            "brand_name": self.brand_name,
            "sku": product_data.get("sku", ""),
            "name": product_data.get("name", ""),
            "collection": product_data.get("collection", ""),
            "source_url": product_data.get("source_url", "")
        }
        json_str = json.dumps(hash_dict, sort_keys=True)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
