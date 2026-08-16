"""Brand Parser Registry for resolving parser instances by brand_key."""
from typing import Dict, Type, List, Optional
from app.domain.carpet_catalog.brand_parser_base import BrandParserBase
from app.domain.carpet_catalog.merinos_parser import MerinosParser


class BrandParserRegistry:
    """Registry mapping brand_key to BrandParserBase implementation."""

    _registry: Dict[str, Type[BrandParserBase]] = {
        "merinos": MerinosParser,
    }

    @classmethod
    def register(cls, brand_key: str, parser_cls: Type[BrandParserBase]) -> None:
        """Register a new brand parser implementation."""
        cls._registry[brand_key.lower().strip()] = parser_cls

    @classmethod
    def get_parser(cls, brand_key: str) -> Optional[BrandParserBase]:
        """Instantiate and return the parser for a given brand_key."""
        key = brand_key.lower().strip()
        parser_cls = cls._registry.get(key)
        if not parser_cls:
            return None
        return parser_cls()

    @classmethod
    def list_registered_brand_keys(cls) -> List[str]:
        """Return list of registered brand keys."""
        return sorted(list(cls._registry.keys()))
