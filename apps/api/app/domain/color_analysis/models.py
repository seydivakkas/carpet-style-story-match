"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Color Observation Domain Models.
Strict Pydantic v2 schemas defining deterministic visual color observations.

SAFETY INVARIANTS:
1. VISIBLE COLOR != DYE MATERIAL
2. COLOR != CULTURAL MEANING
3. dye_material is ALWAYS "UNKNOWN"
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

COLOR_OBSERVATION_SCHEMA_VERSION = "color-observation-v1.0.0"

FORBIDDEN_COLOR_SYMBOLISM_FIELDS = {
    "symbolism", "meaning", "passion", "prosperity", "sacred",
    "blessing", "protection", "nazar", "spiritual_meaning"
}


class ColorObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_id: str
    rgb: List[int] = Field(..., min_length=3, max_length=3)
    hex: str
    hsv: List[int] = Field(..., min_length=3, max_length=3)
    lab: List[float] = Field(..., min_length=3, max_length=3)
    coverage: float = Field(..., ge=0.0, le=1.0)
    perceptual_label: str
    region_scope: str = "CANONICAL_CARPET"
    method: str = "kmeans_cielab_v1"
    analysis_version: str = COLOR_OBSERVATION_SCHEMA_VERSION
    confidence: float = Field(0.9, ge=0.0, le=1.0)
    dye_material: str = "UNKNOWN"

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_color_fields_and_dye(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Reject any forbidden symbolism or cultural meaning fields
            for k in data.keys():
                if k.lower() in FORBIDDEN_COLOR_SYMBOLISM_FIELDS:
                    raise ValueError(f"Forbidden color symbolism field '{k}' detected in ColorObservation.")

            # 2. Enforce dye_material == UNKNOWN
            dye = data.get("dye_material", "UNKNOWN")
            if str(dye).upper() != "UNKNOWN":
                raise ValueError(
                    f"Dye material '{dye}' cannot be inferred from visual pixels. "
                    "VISIBLE COLOR != DYE MATERIAL; dye_material MUST be UNKNOWN."
                )
            data["dye_material"] = "UNKNOWN"
        return data
