"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Source Research Service.
Orchestrates verified motif input gating, query plan generation,
multi-provider retrieval, evidence unit extraction, and EvidencePack assembly.
"""
import logging
from typing import List, Optional, Dict, Any

from app.domain.research.models import (
    ResearchSubject,
    ResearchVerificationStatus,
    ResearchSourceDocument,
    EvidencePack
)
from app.domain.research.query_builder import ResearchQueryBuilder
from app.domain.research.providers import (
    CuratedCorpusResearchProvider,
    DirectOfficialSourceProvider,
    RemoteSearchResearchProvider
)
from app.domain.research.retrieval import EvidenceRetrievalEngine
from app.domain.research.evidence_pack import EvidencePackBuilder

logger = logging.getLogger(__name__)


class SourceResearchService:
    """Service orchestrating source-backed evidence retrieval for verified motifs."""

    def __init__(
        self,
        db_session=None,
        enable_remote_search: bool = False,
        remote_base_url: Optional[str] = None,
        remote_api_key: Optional[str] = None
    ):
        self.curated_provider = CuratedCorpusResearchProvider(db_session=db_session)
        self.direct_provider = DirectOfficialSourceProvider()
        self.remote_provider = RemoteSearchResearchProvider(
            enabled=enable_remote_search,
            base_url=remote_base_url,
            api_key=remote_api_key
        )

    async def execute_research(
        self,
        subject: ResearchSubject,
        direct_url: Optional[str] = None
    ) -> EvidencePack:
        """Executes source research for a verified motif subject and returns an EvidencePack."""
        # 1. INPUT GATE CHECK: Unverified candidates are STRICTLY BLOCKED
        if subject.verification_status not in {ResearchVerificationStatus.CURATOR_CONFIRMED, ResearchVerificationStatus.VERIFIED_CANONICAL}:
            raise ValueError(
                f"Research is BLOCKED for unverified motif candidates ({subject.verification_status.value}). "
                "Research subject MUST be CURATOR_CONFIRMED or VERIFIED_CANONICAL."
            )

        # 2. Generate Neutral Query Plan
        query_plan = ResearchQueryBuilder.build_query_plan(subject)

        documents: List[ResearchSourceDocument] = []
        warnings: List[str] = []

        # 3. Query Curated Corpus Provider
        try:
            curated_docs = await self.curated_provider.search(query_plan)
            documents.extend(curated_docs)
        except Exception as e:
            logger.error(f"CuratedCorpusResearchProvider search failed: {e}")
            warnings.append(f"Curated corpus search warning: {e}")

        # 4. Optional Direct Official Fetch if direct_url supplied
        if direct_url:
            try:
                direct_doc = await self.direct_provider.fetch_document(direct_url)
                if direct_doc:
                    documents.append(direct_doc)
                else:
                    warnings.append(f"Direct URL fetch for '{direct_url}' yielded no document or was rejected by quality filter.")
            except Exception as e:
                logger.error(f"DirectOfficialSourceProvider fetch failed for '{direct_url}': {e}")
                warnings.append(f"Direct fetch error for '{direct_url}': {e}")

        # 5. Optional Remote Search Provider
        if self.remote_provider.enabled:
            try:
                remote_docs = await self.remote_provider.search(query_plan)
                documents.extend(remote_docs)
            except Exception as e:
                logger.error(f"RemoteSearchResearchProvider search failed: {e}")
                warnings.append(f"Remote search warning: {e}")

        # 6. Extract, Chunk, Score, Deduplicate Evidence & Detect Conflicts
        evidence_units, conflicts, coverage = EvidenceRetrievalEngine.extract_evidence(documents, subject)

        # 7. Assemble EvidencePack
        evidence_pack = EvidencePackBuilder.create_pack(
            subject=subject,
            query_plan=query_plan,
            sources=documents,
            evidence_units=evidence_units,
            contradictions=conflicts,
            coverage=coverage,
            warnings=warnings
        )

        return evidence_pack
