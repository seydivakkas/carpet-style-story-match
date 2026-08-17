"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Evidence Retrieval & Chunking Engine.
Extracts copyright-safe evidence units from normalized research documents,
enforces locators, computes scores, deduplicates, and detects evidence conflicts.
"""
import uuid
import hashlib
from typing import List, Tuple, Dict, Any
from app.domain.research.models import (
    ResearchSubject,
    ResearchSourceDocument,
    EvidenceUnit,
    EvidenceConflict,
    SourceTier
)

TIER_BASE_SCORES: Dict[SourceTier, float] = {
    SourceTier.TIER_1_PRIMARY_INSTITUTIONAL: 0.95,
    SourceTier.TIER_2_SCHOLARLY: 0.85,
    SourceTier.TIER_3_REPUTABLE_SECONDARY: 0.70,
    SourceTier.REJECTED_SOURCE: 0.0
}


class EvidenceRetrievalEngine:
    """Extracts, scores, deduplicates, and validates evidence units from research source documents."""

    @classmethod
    def extract_evidence(
        cls,
        documents: List[ResearchSourceDocument],
        subject: ResearchSubject
    ) -> Tuple[List[EvidenceUnit], List[EvidenceConflict], Dict[str, Any]]:
        evidence_units: List[EvidenceUnit] = []
        conflicts: List[EvidenceConflict] = []
        seen_hashes = set()

        tier_1_count = 0
        tier_2_count = 0
        tier_3_count = 0

        for doc in documents:
            if doc.source_tier == SourceTier.REJECTED_SOURCE:
                continue

            if doc.source_tier == SourceTier.TIER_1_PRIMARY_INSTITUTIONAL:
                tier_1_count += 1
            elif doc.source_tier == SourceTier.TIER_2_SCHOLARLY:
                tier_2_count += 1
            elif doc.source_tier == SourceTier.TIER_3_REPUTABLE_SECONDARY:
                tier_3_count += 1

            # Get raw text from provenance or title
            raw_text = doc.provenance.get("extracted_text") or doc.provenance.get("text") or f"{doc.title}. Published by {doc.institution_or_publisher}."

            # Structural chunking by paragraph or section
            chunks = cls._chunk_document_text(raw_text)

            for idx, (locator_label, chunk_text) in enumerate(chunks):
                # Ensure excerpt is copyright-bounded (max ~300 chars)
                excerpt = chunk_text[:300].strip()
                if not excerpt:
                    continue

                c_hash = hashlib.sha256(f"{doc.source_id}_{locator_label}_{excerpt}".encode("utf-8")).hexdigest()
                if c_hash in seen_hashes:
                    continue
                seen_hashes.add(c_hash)

                score = TIER_BASE_SCORES.get(doc.source_tier, 0.70)
                summary = f"Source {doc.institution_or_publisher} documents visual form: {excerpt}"

                ev_id = f"ev-{uuid.uuid4().hex[:8]}"

                unit = EvidenceUnit(
                    evidence_id=ev_id,
                    source_id=doc.source_id,
                    subject_motif_key=subject.canonical_motif_key,
                    locator=locator_label,
                    supporting_excerpt=excerpt,
                    normalized_summary=summary,
                    language=doc.language,
                    retrieval_score=score,
                    source_tier=doc.source_tier,
                    content_hash=c_hash
                )
                evidence_units.append(unit)

        # Contradiction Detection
        conflicts = cls._detect_conflicts(evidence_units, subject)

        total_units = len(evidence_units)
        locator_cov = (sum(1 for u in evidence_units if u.locator) / total_units) if total_units > 0 else 0.0

        coverage = {
            "source_count": len(documents),
            "tier_1_count": tier_1_count,
            "tier_2_count": tier_2_count,
            "tier_3_count": tier_3_count,
            "evidence_unit_count": total_units,
            "locator_coverage": locator_cov,
            "languages_present": list(set(d.language for d in documents))
        }

        return evidence_units, conflicts, coverage

    @classmethod
    def _chunk_document_text(cls, text: str) -> List[Tuple[str, str]]:
        """Splits document text by paragraph boundaries into locator-tagged chunks."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []

        chunks = []
        for i, p in enumerate(paragraphs):
            locator = f"paragraph-{i+1}"
            chunks.append((locator, p))
        return chunks

    @classmethod
    def _detect_conflicts(
        cls,
        units: List[EvidenceUnit],
        subject: ResearchSubject
    ) -> List[EvidenceConflict]:
        """Detects material discrepancies across retrieved evidence units without resolving them."""
        conflicts: List[EvidenceConflict] = []
        if len(units) < 2:
            return conflicts

        # Check for contrasting historical period keywords in excerpts
        period_keywords = {"century", "period", "century", "yüzyıl", "dönem", "safavid", "seljuk", "ottoman"}
        found_terms = set()
        conflicting_ids = []

        for u in units:
            text_lower = u.supporting_excerpt.lower()
            for kw in period_keywords:
                if kw in text_lower:
                    found_terms.add(kw)
                    conflicting_ids.append(u.evidence_id)

        if len(found_terms) > 2 and len(conflicting_ids) >= 2:
            conflicts.append(EvidenceConflict(
                conflict_id=f"conflict-{uuid.uuid4().hex[:8]}",
                subject_motif_key=subject.canonical_motif_key,
                evidence_unit_ids=list(set(conflicting_ids))[:3],
                conflict_type="CONTRADICTORY_HISTORICAL_ATTRIBUTION",
                description="Retrieved evidence contains differing historical period / attribution references across sources."
            ))

        return conflicts
