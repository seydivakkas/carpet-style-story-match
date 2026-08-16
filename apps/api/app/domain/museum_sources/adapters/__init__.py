"""Museum source adapters module."""
from typing import Dict, Type
from app.domain.museum_sources.adapters.base import MuseumSourceAdapter
from app.domain.museum_sources.adapters.met import MetMuseumSourceAdapter
from app.domain.museum_sources.adapters.vam import VAMuseumSourceAdapter

ADAPTER_REGISTRY: Dict[str, Type[MuseumSourceAdapter]] = {
    "met": MetMuseumSourceAdapter,
    "vam": VAMuseumSourceAdapter,
}


def get_adapter(provider_key: str) -> MuseumSourceAdapter:
    """Get adapter instance by provider key."""
    cls = ADAPTER_REGISTRY.get(provider_key.lower())
    if not cls:
        raise ValueError(f"Unknown museum provider key: {provider_key}. Supported: {list(ADAPTER_REGISTRY.keys())}")
    return cls()
