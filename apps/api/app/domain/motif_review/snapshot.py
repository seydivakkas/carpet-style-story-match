"""
Canonical candidate snapshot hashing for Human Motif Review v1.

Produces deterministic SHA-256 hash over candidate identity, visual candidate key,
proposed canonical motif key, candidate status, confidence, region, visual evidence,
model provenance, and ontology version.
FORBIDS volatile fields (timestamps, headers, request IDs, reviewer info).
"""
import hashlib
import json
from typing import Dict, Any, Optional
from app.domain.upload_analysis.schemas import MotifCandidate


def build_canonical_candidate_snapshot(
    candidate: MotifCandidate,
    analysis_id: str,
    ontology_version: str = "motif-ontology-v1.0.0"
) -> Dict[str, Any]:
    """
    Build a deterministic JSON-serializable dictionary representing the exact
    reviewed semantic state of an AI candidate.
    """
    # Extract candidate region safely
    region_dict = None
    if candidate.region is not None:
        polygon_dict = None
        if candidate.region.polygon is not None:
            polygon_dict = candidate.region.polygon.model_dump() if hasattr(candidate.region.polygon, "model_dump") else str(candidate.region.polygon)
        
        region_dict = {
            "bounding_box": candidate.region.bounding_box.model_dump() if candidate.region.bounding_box else None,
            "polygon": polygon_dict,
            "coordinate_space": candidate.region.coordinate_space.value if hasattr(candidate.region.coordinate_space, "value") else str(candidate.region.coordinate_space)
        }


    # Extract visual evidence safely
    visual_evidence_list = []
    if candidate.visual_evidence:
        for ev in candidate.visual_evidence:
            if isinstance(ev, str):
                visual_evidence_list.append(ev)
            elif hasattr(ev, "description"):
                visual_evidence_list.append(ev.description)
            elif isinstance(ev, dict) and "description" in ev:
                visual_evidence_list.append(ev["description"])
            else:
                visual_evidence_list.append(str(ev))
    # Sort visual evidence deterministically
    visual_evidence_list.sort()

    # Extract model provenance
    provenance_dict = {}
    if candidate.model_provenance:
        prov = candidate.model_provenance
        provenance_dict = {
            "provider_type": prov.provider_type.value if hasattr(prov.provider_type, "value") else str(prov.provider_type),
            "model_id": prov.model_id,
            "model_version": getattr(prov, "model_version", "1.0.0"),
            "prompt_version": prov.prompt_version,
            "request_hash": getattr(prov, "request_hash", None)
        }

    status_val = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)

    snapshot = {
        "analysis_id": analysis_id,
        "candidate_id": candidate.candidate_id,
        "visual_candidate_key": candidate.visual_candidate_key.value if hasattr(candidate.visual_candidate_key, "value") else str(candidate.visual_candidate_key),
        "proposed_canonical_motif_key": (
            candidate.proposed_canonical_motif_key.value
            if hasattr(candidate.proposed_canonical_motif_key, "value")
            else candidate.proposed_canonical_motif_key
        ) if candidate.proposed_canonical_motif_key else None,
        "original_candidate_status": status_val,
        "candidate_confidence": round(candidate.confidence, 4),
        "region": region_dict,
        "visual_evidence": visual_evidence_list,
        "model_provenance": provenance_dict,
        "ontology_version": ontology_version
    }

    return snapshot


def compute_snapshot_hash(snapshot: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hex digest over canonical JSON serialization with sorted keys.
    """
    canonical_json_bytes = json.dumps(
        snapshot,
        sort_keys=True,
        ensure_ascii=True,
        separators=(',', ':')
    ).encode('utf-8')

    return hashlib.sha256(canonical_json_bytes).hexdigest()
