"""Abstract Base Class for Manufacturer/Brand Product Catalog Parsers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BrandParserBase(ABC):
    """Abstract base class for brand-specific catalog web scrapers/parsers."""

    @property
    @abstractmethod
    def brand_key(self) -> str:
        """Return canonical brand identifier key e.g. 'merinos'."""
        pass

    @property
    @abstractmethod
    def brand_name(self) -> str:
        """Return official human-readable brand name e.g. 'Merinos'."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return primary official website base URL."""
        pass

    @abstractmethod
    def parse_collection_page(self, html: str, collection_url: str) -> Dict[str, Any]:
        """
        Parse collection HTML page and return structured dictionary with:
        - collection_name: str
        - collection_url: str
        - product_links: List[str]
        """
        pass

    @abstractmethod
    def parse_product_page(
        self,
        html: str,
        product_url: str,
        fallback_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse product HTML page and return factual product metadata dictionary with:
        - sku: str
        - name: str
        - collection: str
        - manufacturer: str
        - source_url: str
        - available_sizes: List[str]
        - primary_image_url: Optional[str]
        - source_hash: str
        """
        pass
