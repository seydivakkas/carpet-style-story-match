"""
Detector Visual Proposal Schema & Contract (v1.0.0)
Defines the output contract for AI motif candidate proposals.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DetectorVisualProposal(BaseModel):
    """
    AI Candidate Visual Motif Proposal contract.
    Strictly visual-only. Zero cultural/historical fields allowed.
    """

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(..., description="Unique proposal identifier")
    visual_candidate_key: str = Field(..., description="One of 17 frozen visual candidate keys")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    bbox: List[float] = Field(..., description="Axis-aligned bounding box [x1, y1, x2, y2] in pixels")
    obb: Optional[List[float]] = Field(default=None, description="Oriented bounding box [8 float coords] in pixels")
    model_id: str = Field(..., description="Detector model name")
    model_version: str = Field(default="1.0.0", description="Model version string")
    experiment_id: str = Field(..., description="Experiment identifier")
    source_image_id: str = Field(..., description="Source image identifier")
    status: str = Field(default="AI_CANDIDATE", description="Always AI_CANDIDATE. Never CURATOR_CONFIRMED.")
