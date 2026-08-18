"""
Annotation DTOs and Schemas for Synthetic Motif Datasets.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


FORBIDDEN_CULTURAL_FIELDS = {
    "culture", "cultural_origin", "dynasty", "historical_period",
    "symbolism", "meaning", "story", "personality", "ethnicity",
    "religion", "authentication", "authenticated_origin", "verified_period",
    "verified_culture", "spiritual_meaning", "blessing"
}


class SyntheticMotifInstanceGT(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    visual_candidate_key: str
    bbox_xyxy: List[float] = Field(..., min_length=4, max_length=4)
    bbox_normalized: List[float] = Field(..., min_length=4, max_length=4)
    polygon: List[List[float]] = Field(..., min_length=3)
    obb: List[List[float]] = Field(..., min_length=4, max_length=4)
    obb_normalized: Optional[List[List[float]]] = None
    mask_ref: Optional[str] = None
    full_geometry: Optional[List[List[float]]] = None
    visible_fraction: float = Field(1.0, ge=0.0, le=1.0)
    is_truncated: bool = False
    is_occluded: bool = False
    ignore: bool = False
    render_parameters: Dict[str, Any] = Field(default_factory=dict)
    transform_provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_cultural_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CULTURAL_FIELDS:
                    raise ValueError(f"Forbidden cultural field '{k}' detected in SyntheticMotifInstanceGT.")
        return data


class HardNegativeProvenanceGT(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_negative_id: str
    hard_negative_key: str
    near_target_keys: List[str]
    bbox_xyxy: Optional[List[float]] = Field(default=None, min_length=4, max_length=4)
    polygon: Optional[List[List[float]]] = None
    render_parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_cultural_fields_hn(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CULTURAL_FIELDS:
                    raise ValueError(f"Forbidden cultural field '{k}' detected in HardNegativeProvenanceGT.")
        return data


class SyntheticCarpetSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str
    seed: int
    split: str = "train"
    image_width: int = 640
    image_height: int = 640
    image_ref: str
    mask_ref: Optional[str] = None
    generator_version: str = "procedural-motif-generator-v1.0.0"
    registry_version: str = "synthetic-motif-registry-v1.0.0"
    scene_signature: str
    scene_spec: Dict[str, Any] = Field(default_factory=dict)
    randomization_profile: Dict[str, Any] = Field(default_factory=dict)
    artifact_hashes: Dict[str, str] = Field(default_factory=dict)
    instances: List[SyntheticMotifInstanceGT] = Field(default_factory=list)
    hard_negatives: List[HardNegativeProvenanceGT] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_cultural_fields_sample(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_CULTURAL_FIELDS:
                    raise ValueError(f"Forbidden cultural field '{k}' detected in SyntheticCarpetSample.")
        return data
