"""VAMuseumSourceAdapter for Victoria and Albert Museum Collections API v1."""
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


def _clean_string(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip() or None
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        items = [_clean_string(item) for item in val if item is not None]
        items = [i for i in items if i]
        return ", ".join(items) if items else None
    if isinstance(val, dict):
        if "text" in val:
            return _clean_string(val["text"])
        if "dimension" in val:
            dim_name = val.get("dimension", "")
            dim_val = val.get("value", "")
            dim_unit = val.get("unit", "")
            return f"{dim_name}: {dim_val} {dim_unit}".strip()
        return str(val)
    return str(val)


class VAMuseumSourceAdapter(MuseumSourceAdapter):
    """Adapter for Victoria and Albert Museum (V&A) Collections API."""

    @property
    def provider_key(self) -> str:
        return "vam"

    @property
    def institution_name(self) -> str:
        return "Victoria and Albert Museum"

    @property
    def official_base_url(self) -> str:
        return "https://collections.vam.ac.uk"

    def search_objects(self, query: str = "carpet", limit: int = 20) -> List[str]:
        url = f"https://api.vam.ac.uk/v2/objects/search?q={urllib.parse.quote(query)}&kw_object_type=carpet&page_size={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "CarpetStyleStoryMatch/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                records = data.get("records") or []
                return [r.get("systemNumber") for r in records if r.get("systemNumber")]
        except Exception:
            return []

    def fetch_object_raw(self, object_id: str) -> Dict[str, Any]:
        url = f"https://api.vam.ac.uk/v2/object/{object_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "CarpetStyleStoryMatch/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def normalize_object(self, raw_data: Dict[str, Any]) -> MuseumObjectSourceRecord:
        record_obj = raw_data.get("record") or raw_data
        system_no = record_obj.get("systemNumber") or record_obj.get("accessionNumber")
        if not system_no:
            return MuseumObjectSourceRecord(
                source_key=f"vam-object-invalid-{record_obj.get('accessionNumber', 'unknown')}",
                provider_key=self.provider_key,
                institution_name=self.institution_name,
                official_object_id="UNKNOWN",
                object_title="Invalid Record",
                object_url=self.official_base_url,
                source_record_hash="invalid",
                acquisition_status=AcquisitionStatusEnum.INVALID_RECORD,
                a7_readiness=A7ReadinessEnum.NOT_ELIGIBLE,
                rejection_reason="Missing official systemNumber"
            )

        sys_no_str = str(system_no)
        accession_no = _clean_string(record_obj.get("accessionNumber")) or sys_no_str
        title_raw = record_obj.get("objectType") or record_obj.get("title") or f"V&A Carpet Object {sys_no_str}"
        title = _clean_string(title_raw) or f"V&A Carpet Object {sys_no_str}"

        obj_type = _clean_string(record_obj.get("objectType")) or ""

        obj_type_lower = obj_type.lower()
        title_lower = title.lower()

        rejection_reason = None
        is_carpet_relevant = False

        carpet_keywords = ["carpet", "rug", "prayer rug", "floor covering", "textile", "pile"]
        non_carpet_keywords = ["painting", "photograph", "book", "print", "drawing", "sculpture", "vase"]

        if any(nk in obj_type_lower for nk in non_carpet_keywords):
            rejection_reason = f"Object type is not a carpet ({obj_type})"
        elif any(ck in obj_type_lower or ck in title_lower for ck in carpet_keywords):
            is_carpet_relevant = True
        else:
            rejection_reason = f"Object type does not indicate carpet textile ({obj_type})"

        status = AcquisitionStatusEnum.ACCEPTED if is_carpet_relevant else AcquisitionStatusEnum.REJECTED_NOT_CARPET
        readiness = A7ReadinessEnum.READY_FOR_HISTORICAL_CURATION if is_carpet_relevant else A7ReadinessEnum.NOT_ELIGIBLE

        source_key = f"vam-object-{sys_no_str}"

        # Extract culture from placesOfOrigin or productionPlaces
        places = record_obj.get("placesOfOrigin") or record_obj.get("productionPlaces") or []
        culture = None
        if places and isinstance(places, list):
            place_names = [p.get("place", {}).get("text") for p in places if isinstance(p, dict) and p.get("place", {}).get("text")]
            if place_names:
                culture = ", ".join(place_names)

        date_text = _clean_string(record_obj.get("dateText") or (record_obj.get("productionDates", [{}])[0].get("date", {}).get("text") if record_obj.get("productionDates") else None))

        # Rights Metadata
        image_info = raw_data.get("images") or record_obj.get("_images") or []
        has_images = bool(image_info)
        rights_meta = RightsMetadata(
            open_access=False,  # V&A requires academic/educational licensing check
            public_domain=False,
            rights_statement="Victoria and Albert Museum, London / Non-Commercial Educational Reuse",
            image_reuse_status="RIGHTS_REVIEW_REQUIRED" if has_images else "NO_IMAGE_REFERENCE",
            rights_source=self.institution_name
        )

        primary_img_url = None
        if has_images and isinstance(image_info, list) and len(image_info) > 0:
            first_img = image_info[0]
            if isinstance(first_img, dict):
                primary_img_url = first_img.get("image_id") or first_img.get("url")
                if primary_img_url and not primary_img_url.startswith("http"):
                    primary_img_url = f"https://framemark.vam.ac.uk/collections/{primary_img_url}/full/full/0/default.jpg"

        object_web_url = f"https://collections.vam.ac.uk/item/{sys_no_str}"

        medium_text = _clean_string(record_obj.get("materialsAndTechniques"))
        dimensions_text = _clean_string(record_obj.get("dimensions"))
        department_text = _clean_string(record_obj.get("department"))
        credit_line_text = _clean_string(record_obj.get("creditLine"))
        period_text = _clean_string(record_obj.get("period"))

        rec_dict = {
            "source_key": source_key,
            "provider_key": self.provider_key,
            "institution_name": self.institution_name,
            "official_object_id": sys_no_str,
            "accession_number": accession_no,
            "object_title": title,
            "object_url": object_web_url,
            "source_type": "MUSEUM_OBJECT",
            "object_type": obj_type or None,
            "culture": culture,
            "period": period_text,
            "dynasty_or_tradition": None,
            "date_display": date_text,
            "geography": culture,
            "medium": medium_text,
            "dimensions_text": dimensions_text,
            "department": department_text,
            "credit_line": credit_line_text,
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
            official_object_id=sys_no_str,
            accession_number=accession_no,
            object_title=title,
            object_url=object_web_url,
            source_type="MUSEUM_OBJECT",
            object_type=obj_type or None,
            culture=culture,
            period=period_text,
            dynasty_or_tradition=None,
            date_display=date_text,
            geography=culture,
            medium=medium_text,
            dimensions_text=dimensions_text,
            department=department_text,
            credit_line=credit_line_text,
            rights=rights_meta,
            primary_image_source_url=primary_img_url,
            source_record_hash=record_hash,
            acquisition_status=status,
            a7_readiness=readiness,
            rejection_reason=rejection_reason
        )
