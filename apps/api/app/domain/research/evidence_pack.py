"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 EvidencePack Builder & Schema Validation Utilities.
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.domain.research.models import (
    ResearchSubject,
    ResearchQueryPlan,
    ResearchSourceDocument,
    EvidenceUnit,
    EvidenceConflict,
    EvidencePack,
    EVIDENCE_PACK_SCHEMA_VERSION,
    ResearchVerificationStatus
)

logger = logging.getLogger(__name__)


class EvidencePackBuilder:
    """Builds and validates strict evidence-pack-v1.0.0 artifacts."""

    @classmethod
    def create_pack(
        cls,
        subject: ResearchSubject,
        query_plan: ResearchQueryPlan,
        sources: List[ResearchSourceDocument],
        evidence_units: List[EvidenceUnit],
        contradictions: List[EvidenceConflict],
        coverage: Dict[str, Any],
        warnings: Optional[List[str]] = None
    ) -> EvidencePack:
        # Enforce subject verification gate
        if subject.verification_status not in {ResearchVerificationStatus.CURATOR_CONFIRMED, ResearchVerificationStatus.VERIFIED_CANONICAL}:
            raise ValueError(f"Research subject '{subject.canonical_motif_key}' status '{subject.verification_status}' is NOT research eligible. Subject must be CURATOR_CONFIRMED or VERIFIED_CANONICAL.")

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        prov = {
            "query_plan_version": query_plan.query_plan_version,
            "evidence_pack_version": EVIDENCE_PACK_SCHEMA_VERSION,
            "retrieved_at": timestamp,
            "retrieval_algorithm_version": "hybrid-retrieval-v1.0.0",
            "source_count": len(sources),
            "evidence_count": len(evidence_units)
        }

        pack = EvidencePack(
            schema_version=EVIDENCE_PACK_SCHEMA_VERSION,
            research_run_id=run_id,
            subject=subject,
            query_plan=query_plan,
            sources=sources,
            evidence_units=evidence_units,
            contradictions=contradictions,
            coverage=coverage,
            provenance=prov,
            warnings=warnings or []
        )

        return pack

    @classmethod
    def generate_json_schema(cls) -> Dict[str, Any]:
        """Generates Pydantic v2 JSON Schema for evidence-pack-v1.0.0."""
        return EvidencePack.model_json_schema()
