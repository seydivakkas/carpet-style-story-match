"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Carpet Analysis Orchestrator.
Coordinates quality preparation, Style DNA 9D, deterministic color observation,
reference VLM motif proposal, and verified motif source research.

SAFETY INVARIANT:
Does NOT automatically promote VLM AI candidates to verified research subjects.
An explicit review gate (CURATOR_CONFIRMED / VERIFIED_CANONICAL) is required.
"""
import logging
from typing import Dict, Any, List, Optional

from app.domain.upload_analysis.image_preparation import prepare_image_for_vlm
from app.domain.styledna.engine import StyleDNAEngine
from app.domain.color_analysis.service import ColorAnalysisService
from app.domain.upload_analysis.vlm_provider import MotifVisionProvider
from app.domain.research.models import ResearchSubject, ResearchVerificationStatus
from app.domain.research.service import SourceResearchService

logger = logging.getLogger(__name__)


class CarpetAnalysisOrchestrator:
    """Developer-stage orchestrator coordinating modular domain analysis services."""

    def __init__(
        self,
        style_dna_engine: Optional[StyleDNAEngine] = None,
        color_service: Optional[ColorAnalysisService] = None,
        vlm_provider: Optional[MotifVisionProvider] = None,
        research_service: Optional[SourceResearchService] = None
    ):
        self.style_dna_engine = style_dna_engine or StyleDNAEngine()
        self.color_service = color_service or ColorAnalysisService()
        self.vlm_provider = vlm_provider
        self.research_service = research_service or SourceResearchService()

    async def run_pipeline(
        self,
        raw_bytes: bytes,
        mime_type: str = "image/jpeg",
        stages: Optional[List[str]] = None,
        verified_subject_motif: Optional[str] = None
    ) -> Dict[str, Any]:
        stages = stages or ["visual"]
        output: Dict[str, Any] = {
            "orchestrator_version": "carpet-orchestrator-v1.0.0",
            "stages_executed": []
        }

        # 1. Quality & Image Preparation Stage
        prepared = prepare_image_for_vlm(raw_bytes, mime_type)
        output["image_meta"] = {
            "original_sha256": prepared.original_sha256,
            "prepared_sha256": prepared.prepared_sha256,
            "original_width": prepared.original_width,
            "original_height": prepared.original_height,
            "prepared_width": prepared.prepared_width,
            "prepared_height": prepared.prepared_height
        }

        # 2. Visual Stage (Style DNA 9D + Deterministic Color Observations)
        if "visual" in stages:
            # Style DNA
            dna_status, dna_dims = self.style_dna_engine.analyze(raw_bytes)
            output["style_dna"] = {
                "status": dna_status.value if hasattr(dna_status, "value") else str(dna_status),
                "dimensions": dna_dims
            }

            # Color Observations
            colors = self.color_service.analyze_colors(raw_bytes)
            output["color_observations"] = [c.model_dump() for c in colors]
            output["stages_executed"].append("visual")

        # 3. Motif Stage (VLM Candidate Proposals)
        if "motif" in stages:
            if self.vlm_provider:
                try:
                    vlm_res = await self.vlm_provider.analyze(prepared)
                    output["vlm_motif_analysis"] = vlm_res.model_dump()
                except Exception as e:
                    output["vlm_motif_analysis"] = {"status": "ERROR", "error": str(e)}
            else:
                output["vlm_motif_analysis"] = {"status": "DISABLED", "message": "VLM provider not configured."}
            output["stages_executed"].append("motif")

        # 4. Research Stage (Requires Verified ResearchSubject - DOES NOT AUTO-PROMOTE AI CANDIDATE)
        if "research" in stages:
            if verified_subject_motif:
                subject = ResearchSubject(
                    subject_id=f"subj-cli-{verified_subject_motif}",
                    canonical_motif_key=verified_subject_motif,
                    verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
                    display_name=verified_subject_motif.replace("_", " ").title(),
                    created_at=output.get("timestamp", "2026-08-17T11:00:00Z")
                )
                try:
                    pack = await self.research_service.execute_research(subject)
                    output["evidence_pack"] = pack.model_dump()
                except Exception as e:
                    output["evidence_pack"] = {"status": "ERROR", "error": str(e)}
            else:
                output["evidence_pack"] = {
                    "status": "BLOCKED_NOT_VERIFIED",
                    "message": "Research stage requires an explicit verified subject motif key (--subject-motif). AI candidates cannot auto-trigger research."
                }
            output["stages_executed"].append("research")

        return output
