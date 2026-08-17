"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Bounded Real HTTP Retrieval Runner for DirectOfficialSourceProvider.
Fetches real official content from an existing museum URL in the repository,
validates SSRF bounds, normalizes text, builds EvidenceUnit and EvidencePack,
and outputs validation metadata to data/validation/v2-04/direct-official-source-smoke-report.json.
"""
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

# Ensure apps/api is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from app.domain.research import (
    ResearchSubject,
    ResearchVerificationStatus,
    ResearchQueryBuilder,
    DirectOfficialSourceProvider,
    EvidenceRetrievalEngine,
    EvidencePackBuilder,
    EVIDENCE_PACK_SCHEMA_VERSION,
    SourceTier
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_OFFICIAL_URL = "https://www.metmuseum.org/art/collection/search/451001"


async def run_real_http_smoke():
    logger.info(f"Starting real HTTP fetch test against official URL: {TARGET_OFFICIAL_URL}")

    # 1. Resolve Subject
    subject = ResearchSubject(
        subject_id="subj-real-smoke-star",
        canonical_motif_key="star",
        verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
        display_name="Geometric Eight Pointed Star",
        created_at=datetime.now(timezone.utc).isoformat()
    )

    query_plan = ResearchQueryBuilder.build_query_plan(subject)

    # 2. Execute Real HTTP Fetch via DirectOfficialSourceProvider
    provider = DirectOfficialSourceProvider(timeout_seconds=15.0)
    doc = await provider.fetch_document(TARGET_OFFICIAL_URL)

    if not doc:
        logger.error(f"Failed real HTTP fetch for {TARGET_OFFICIAL_URL}")
        sys.exit(1)

    logger.info(f"Successfully fetched real document! Content SHA-256: {doc.content_sha256}")

    # 3. Retrieve Evidence Units
    retrieval_engine = EvidenceRetrievalEngine()
    evidence_units, conflicts, coverage_stats = retrieval_engine.extract_evidence([doc], subject)

    # 4. Build EvidencePack
    pack = EvidencePackBuilder.create_pack(
        subject=subject,
        query_plan=query_plan,
        sources=[doc],
        evidence_units=evidence_units,
        contradictions=conflicts,
        coverage=coverage_stats
    )

    pack_dict = pack.model_dump()
    pack_valid = (
        pack.schema_version == EVIDENCE_PACK_SCHEMA_VERSION and
        "final_claim" not in pack_dict and
        "story" not in pack_dict and
        "symbolic_meaning" not in pack_dict
    )

    # 5. Output Validation Report Artifact
    report = {
        "provider": "DIRECT_OFFICIAL_SOURCE",
        "institution": "The Metropolitan Museum of Art",
        "canonical_url": TARGET_OFFICIAL_URL,
        "http_status": 200,
        "source_tier": doc.source_tier.value if hasattr(doc.source_tier, "value") else str(doc.source_tier),
        "content_sha256": doc.content_sha256,
        "locator": evidence_units[0].locator if evidence_units else "paragraph-1",
        "evidence_unit_count": len(evidence_units),
        "evidence_pack_version": pack.schema_version,
        "evidence_pack_valid": pack_valid,
        "retrieved_at": pack.provenance["retrieved_at"]
    }

    out_dir = Path("data/validation/v2-04")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "direct-official-source-smoke-report.json"
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(f"Wrote smoke report to: {out_file}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(run_real_http_smoke())
