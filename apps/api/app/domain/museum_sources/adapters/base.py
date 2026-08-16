"""Abstract base protocol for official institutional Museum Source Adapters."""
from abc import ABC, abstractmethod
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from app.domain.motif_knowledge.schemas import SourceImportItem
from app.domain.museum_sources.schemas import (
    MuseumObjectSourceRecord,
    AcquisitionStatusEnum,
    A7ReadinessEnum,
    RightsMetadata,
)


class MuseumSourceAdapter(ABC):
    """Abstract protocol for official institutional museum API adapters."""

    @property
    @abstractmethod
    def provider_key(self) -> str:
        """Stable provider identifier (e.g. 'met', 'vam')."""
        pass

    @property
    @abstractmethod
    def institution_name(self) -> str:
        """Official institution display name."""
        pass

    @property
    @abstractmethod
    def official_base_url(self) -> str:
        """Official base URL or portal URL."""
        pass

    @abstractmethod
    def search_objects(self, query: str, limit: int = 20) -> List[str]:
        """Search for relevant candidate object IDs."""
        pass

    @abstractmethod
    def fetch_object_raw(self, object_id: str) -> Dict[str, Any]:
        """Fetch raw JSON payload for an object ID."""
        pass

    @abstractmethod
    def normalize_object(self, raw_data: Dict[str, Any]) -> MuseumObjectSourceRecord:
        """Normalize raw museum object payload into MuseumObjectSourceRecord."""
        pass

    def compute_record_hash(self, record_dict: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash over normalized factual fields for drift detection."""
        # Clean transient fields before hashing
        hashable = {
            k: v for k, v in record_dict.items()
            if k not in ("retrieved_at", "source_record_hash")
        }
        canonical_str = json.dumps(hashable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def build_curated_source_input(self, record: MuseumObjectSourceRecord) -> SourceImportItem:
        """Convert normalized MuseumObjectSourceRecord into existing SourceImportItem."""
        citation_parts = [
            f"{record.institution_name}.",
            f'"{record.object_title}".',
            f"Object ID: {record.official_object_id}."
        ]
        if record.accession_number:
            citation_parts.append(f"Accession No: {record.accession_number}.")
        if record.date_display:
            citation_parts.append(f"Date: {record.date_display}.")
        if record.culture:
            citation_parts.append(f"Culture: {record.culture}.")

        citation_text = " ".join(citation_parts)

        # Parse publication year if available, otherwise None (no date parsing guess)
        pub_year = None
        if record.date_display and record.date_display.isdigit():
            pub_year = int(record.date_display)

        rights_str = record.rights.rights_statement or f"Open Access: {record.rights.open_access}, Public Domain: {record.rights.public_domain}"

        return SourceImportItem(
            source_key=record.source_key,
            source_type="MUSEUM_OBJECT",
            title=record.object_title,
            citation_text=citation_text[:1000],
            creator_or_institution=record.institution_name,
            publication_year=pub_year,
            url=record.object_url,
            doi=None,
            isbn=None,
            rights_note=rights_str[:500] if rights_str else None
        )
