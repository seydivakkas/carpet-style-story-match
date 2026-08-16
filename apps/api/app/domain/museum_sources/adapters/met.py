"""MetMuseumSourceAdapter for The Metropolitan Museum of Art Open Access API v1."""
import json
import urllib.request
from typing import Dict, List, Optional, Any
from app.domain.museum_sources.adapters.base import MuseumSourceAdapter
from app.domain.museum_sources.schemas import (
    MuseumObjectSourceRecord,
    AcquisitionStatusEnum,
    A7ReadinessEnum,
    RightsMetadata,
)


class MetMuseumSourceAdapter(MuseumSourceAdapter):
    """Adapter for The Metropolitan Museum of Art Collection API."""

    @property
    def provider_key(self) -> str:
        return "met"

    @property
    def institution_name(self) -> str:
        return "The Metropolitan Museum of Art"

    @property
    def official_base_url(self) -> str:
        return "https://www.metmuseum.org"

    def search_objects(self, query: str = "carpet", limit: int = 20) -> List[str]:
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?hasImages=true&q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "CarpetStyleStoryMatch/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                object_ids = data.get("objectIDs") or []
                return [str(oid) for oid in object_ids[:limit]]
        except Exception:
            return []

    def fetch_object_raw(self, object_id: str) -> Dict[str, Any]:
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "CarpetStyleStoryMatch/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def normalize_object(self, raw_data: Dict[str, Any]) -> MuseumObjectSourceRecord:
        oid = raw_data.get("objectID")
        if not oid:
            return MuseumObjectSourceRecord(
                source_key=f"met-object-invalid-{raw_data.get('accessionNumber', 'unknown')}",
                provider_key=self.provider_key,
                institution_name=self.institution_name,
                official_object_id="UNKNOWN",
                object_title="Invalid Record",
                object_url=self.official_base_url,
                source_record_hash="invalid",
                acquisition_status=AcquisitionStatusEnum.INVALID_RECORD,
                a7_readiness=A7ReadinessEnum.NOT_ELIGIBLE,
                rejection_reason="Missing official objectID"
            )

        oid_str = str(oid)
        accession_no = raw_data.get("accessionNumber")
        title = raw_data.get("title") or f"Carpet/Textile Object {oid_str}"
        obj_name = (raw_data.get("objectName") or "").strip()
        classification = (raw_data.get("classification") or "").strip()

        # Check for false positives: paintings, books, photographs, drawings
        obj_name_lower = obj_name.lower()
        class_lower = classification.lower()
        title_lower = title.lower()

        rejection_reason = None
        is_carpet_relevant = False

        # Must describe a carpet/rug/textile floor covering
        carpet_keywords = ["carpet", "rug", "prayer rug", "floor covering", "textiles-rugs", "knotted pile"]
        non_carpet_keywords = ["painting", "photograph", "book", "print", "drawing", "sculpture", "vase", "miniature", "manuscript"]

        if any(nk in obj_name_lower or nk in class_lower for nk in non_carpet_keywords):
            rejection_reason = f"Object classification is not a carpet ({obj_name} / {classification})"
        elif any(ck in obj_name_lower or ck in class_lower or ck in title_lower for ck in carpet_keywords):
            is_carpet_relevant = True
        else:
            rejection_reason = f"Object name/classification does not indicate carpet textile ({obj_name} / {classification})"

        status = AcquisitionStatusEnum.ACCEPTED if is_carpet_relevant else AcquisitionStatusEnum.REJECTED_NOT_CARPET
        readiness = A7ReadinessEnum.READY_FOR_HISTORICAL_CURATION if is_carpet_relevant else A7ReadinessEnum.NOT_ELIGIBLE

        # Source Key: Handle special A4A existing Met Safavid Medallion Carpet (Acc 14.40.714 / Object ID 446561)
        if oid_str == "446561" or (accession_no and "14.40.714" in accession_no):
            source_key = "met-museum-safavid-medallion-carpet-14104"
        else:
            source_key = f"met-object-{oid_str}"

        # Rights Metadata (separated from image reuse)
        is_pub_domain = raw_data.get("isPublicDomain")
        rights_meta = RightsMetadata(
            open_access=is_pub_domain,
            public_domain=is_pub_domain,
            rights_statement=raw_data.get("rightsAndReproduction") or ("CC0 1.0 Universal" if is_pub_domain else "All Rights Reserved"),
            image_reuse_status="OPEN_ACCESS_PUBLIC_DOMAIN" if is_pub_domain else "RIGHTS_REVIEW_REQUIRED",
            rights_source=self.institution_name
        )

        primary_img_url = raw_data.get("primaryImage") or raw_data.get("primaryImageSmall") or None
        object_web_url = raw_data.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{oid_str}"

        rec_dict = {
            "source_key": source_key,
            "provider_key": self.provider_key,
            "institution_name": self.institution_name,
            "official_object_id": oid_str,
            "accession_number": accession_no,
            "object_title": title,
            "object_url": object_web_url,
            "source_type": "MUSEUM_OBJECT",
            "object_type": obj_name or classification or None,
            "culture": raw_data.get("culture") or None,
            "period": raw_data.get("period") or None,
            "dynasty_or_tradition": raw_data.get("dynasty") or None,
            "date_display": raw_data.get("objectDate") or None,
            "geography": raw_data.get("country") or raw_data.get("region") or None,
            "medium": raw_data.get("medium") or None,
            "dimensions_text": raw_data.get("dimensions") or None,
            "department": raw_data.get("department") or None,
            "credit_line": raw_data.get("creditLine") or None,
            "rights": rights_meta.model_dump(),
            "primary_image_source_url": primary_img_url,
            "acquisition_status": status.value,
            "a7_readiness": readiness.value,
            "rejection_reason": rejection_reason
        }

        record_hash = self.compute_record_hash(rec_dict)

        return MuseumObjectSourceRecord(
            source_key=source_key,
            provider_key=self.provider_key,
            institution_name=self.institution_name,
            official_object_id=oid_str,
            accession_number=accession_no,
            object_title=title,
            object_url=object_web_url,
            source_type="MUSEUM_OBJECT",
            object_type=obj_name or classification or None,
            culture=raw_data.get("culture") or None,
            period=raw_data.get("period") or None,
            dynasty_or_tradition=raw_data.get("dynasty") or None,
            date_display=raw_data.get("objectDate") or None,
            geography=raw_data.get("country") or raw_data.get("region") or None,
            medium=raw_data.get("medium") or None,
            dimensions_text=raw_data.get("dimensions") or None,
            department=raw_data.get("department") or None,
            credit_line=raw_data.get("creditLine") or None,
            rights=rights_meta,
            primary_image_source_url=primary_img_url,
            source_record_hash=record_hash,
            acquisition_status=status,
            a7_readiness=readiness,
            rejection_reason=rejection_reason
        )
