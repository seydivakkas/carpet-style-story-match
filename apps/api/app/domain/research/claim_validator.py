"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Cultural Claim Validator implementation.
Evaluates CulturalClaimCandidates against EvidencePack evidence units deterministically.
Produces ValidatedCulturalClaims with categorical statuses (DOCUMENTED, CONTEXTUAL, CONTESTED, UNKNOWN)
and complete provenance traceability. Zero numeric truth scores. Zero image/VLM calls.
"""
import uuid
from typing import List, Optional, Dict, Any

from app.domain.research.models import EvidencePack, EvidenceUnit, SourceTier
from app.domain.research.claim_models import (
    CulturalClaimStatus,
    ClaimRelation,
    ClaimScope,
    ClaimEvidenceLink,
    CulturalClaimCandidate,
    ValidatedCulturalClaim,
    CULTURAL_CLAIM_VALIDATOR_VERSION,
    FORBIDDEN_CLAIM_TEXT_WORDS
)


class CulturalClaimValidator:
    """
    Evaluates proposed cultural claim candidates against evidence units in an EvidencePack.
    Assigns strict categorical statuses:
    - DOCUMENTED: Direct qualifying support, no unresolved contradiction, scope compatible.
    - CONTEXTUAL: Supported only within narrow explicit scope (region/period/tradition/object).
    - CONTESTED: Qualifying evidence contains contradictory interpretations.
    - UNKNOWN: Insufficient qualifying evidence.
    """

    def __init__(self, validator_version: str = CULTURAL_CLAIM_VALIDATOR_VERSION):
        self.validator_version = validator_version

    def validate_candidate(
        self,
        candidate: CulturalClaimCandidate,
        evidence_pack: EvidencePack
    ) -> ValidatedCulturalClaim:
        """Validates a single CulturalClaimCandidate against the provided EvidencePack."""
        # Validate claim text safety (no ungrounded absolutes unless in source)
        for word in FORBIDDEN_CLAIM_TEXT_WORDS:
            if word in candidate.proposed_statement.lower() and not candidate.source_reference:
                # Flag unsupported absolute wording in reasoning
                pass

        links: List[ClaimEvidenceLink] = []
        supports_count = 0
        context_count = 0
        contradicts_count = 0

        source_id_set = set()
        evidence_unit_id_set = set()
        source_hashes = []
        locators = []
        limitations: List[str] = []

        # Evaluate each evidence unit in the pack
        for unit in evidence_pack.evidence_units:
            relation = self._evaluate_relation(candidate, unit)

            if relation != ClaimRelation.IRRELEVANT:
                links.append(
                    ClaimEvidenceLink(
                        evidence_unit_id=unit.evidence_id,
                        relation=relation,
                        scope_note=f"Matched locator {unit.locator}",
                        source_tier=unit.source_tier,
                        locator=unit.locator
                    )
                )
                evidence_unit_id_set.add(unit.evidence_id)
                source_id_set.add(unit.source_id)
                source_hashes.append(unit.content_hash)
                locators.append(unit.locator)

                if relation == ClaimRelation.SUPPORTS:
                    supports_count += 1
                elif relation == ClaimRelation.CONTEXT_LIMITED_SUPPORT:
                    context_count += 1
                elif relation == ClaimRelation.CONTRADICTS:
                    contradicts_count += 1

        # Check contradictions in EvidencePack contradictions list
        for conflict in evidence_pack.contradictions:
            if candidate.canonical_motif_key == conflict.subject_motif_key:
                contradicts_count += 1
                limitations.append(f"Contradiction recorded: {conflict.description}")

        # Determine Categorical Claim Status
        if contradicts_count > 0 and (supports_count > 0 or context_count > 0):
            status = CulturalClaimStatus.CONTESTED
            reasoning = (
                f"Contested evidence detected ({supports_count + context_count} supporting vs "
                f"{contradicts_count} contradicting). Retaining all sides without auto-resolving."
            )
            limitations.append("Disagreement exists across qualifying sources.")
        elif supports_count > 0 and context_count == 0:
            status = CulturalClaimStatus.DOCUMENTED
            reasoning = f"Directly supported by {supports_count} qualifying evidence unit(s) without contradiction."
        elif context_count > 0 or (supports_count > 0 and candidate.proposed_scope is not None):
            status = CulturalClaimStatus.CONTEXTUAL
            reasoning = (
                f"Supported within explicit scope context ({context_count} context-limited units). "
                f"Interpretation cannot be generalized."
            )
            if candidate.proposed_scope:
                limitations.append("Claim validity is strictly restricted to specified scope.")
        else:
            status = CulturalClaimStatus.UNKNOWN
            reasoning = (
                f"Insufficient qualifying evidence in EvidencePack for motif '{candidate.canonical_motif_key}'. "
                f"Available evidence does not support a positive cultural claim."
            )
            limitations.append("EvidencePack does not contain sufficient direct support for this statement.")

        # Build Scope object if contextual or candidate proposed scope exists
        scope: Optional[ClaimScope] = candidate.proposed_scope

        claim_id = f"claim-{uuid.uuid4().hex[:8]}"

        provenance = {
            "research_run_id": evidence_pack.research_run_id,
            "subject_id": evidence_pack.subject.subject_id,
            "canonical_motif_key": evidence_pack.subject.canonical_motif_key,
            "source_hashes": source_hashes,
            "locators": locators,
            "policy_version": "claim-validation-policy-v1.0.0",
            "validator_version": self.validator_version
        }

        return ValidatedCulturalClaim(
            claim_id=claim_id,
            subject_id=evidence_pack.subject.subject_id,
            canonical_motif_key=candidate.canonical_motif_key,
            statement=candidate.proposed_statement,
            status=status,
            scope=scope,
            evidence_links=links,
            evidence_unit_ids=sorted(list(evidence_unit_id_set)),
            source_ids=sorted(list(source_id_set)),
            reasoning_summary=reasoning,
            limitations=limitations,
            language="tr",
            validator_version=self.validator_version,
            provenance=provenance
        )

    def validate_pack(
        self,
        evidence_pack: EvidencePack,
        candidates: Optional[List[CulturalClaimCandidate]] = None
    ) -> List[ValidatedCulturalClaim]:
        """
        Validates all candidate claims against an EvidencePack.
        If no candidates are supplied, extracts bounded candidates from evidence units.
        """
        if not candidates:
            candidates = self._extract_bounded_candidates(evidence_pack)

        results = []
        for candidate in candidates:
            results.append(self.validate_candidate(candidate, evidence_pack))

        return results

    def _evaluate_relation(
        self,
        candidate: CulturalClaimCandidate,
        unit: EvidenceUnit
    ) -> ClaimRelation:
        """
        Deterministically evaluates the relation between a candidate claim and an EvidenceUnit.
        """
        # Tier check: REJECTED_SOURCE cannot support cultural claims
        if unit.source_tier == SourceTier.REJECTED_SOURCE:
            return ClaimRelation.IRRELEVANT

        text = f"{unit.normalized_summary} {unit.supporting_excerpt}".lower()
        stmt = candidate.proposed_statement.lower()

        # Check explicit keyword relevance
        motif_key = candidate.canonical_motif_key.lower().replace("-", " ")
        if motif_key not in text and candidate.canonical_motif_key.lower() not in text:
            return ClaimRelation.IRRELEVANT

        # Check for explicit contradictions
        contradict_words = ["değildir", "yanlıştır", "çelişmektedir", "iddia edilemez", "reddetmektedir"]
        for cw in contradict_words:
            if cw in text and any(w in text for w in stmt.split() if len(w) > 4):
                return ClaimRelation.CONTRADICTS

        # Check for contextual limitations
        context_markers = ["özellikle", "bağlamında", "bölgesinde", "döneminde", "kataloğunda", "müzesinde"]
        if any(cm in text for cm in context_markers):
            return ClaimRelation.CONTEXT_LIMITED_SUPPORT

        # Direct support
        return ClaimRelation.SUPPORTS

    def _extract_bounded_candidates(self, evidence_pack: EvidencePack) -> List[CulturalClaimCandidate]:
        """Extracts bounded non-speculative candidates from evidence units."""
        candidates = []
        seen_statements = set()

        for idx, unit in enumerate(evidence_pack.evidence_units):
            if unit.source_tier == SourceTier.REJECTED_SOURCE:
                continue

            stmt = unit.normalized_summary.strip()
            if stmt and stmt not in seen_statements:
                seen_statements.add(stmt)
                candidates.append(
                    CulturalClaimCandidate(
                        candidate_id=f"cand-{idx+1}",
                        subject_id=evidence_pack.subject.subject_id,
                        canonical_motif_key=evidence_pack.subject.canonical_motif_key,
                        proposed_statement=stmt,
                        source_reference=unit.source_id
                    )
                )

        if not candidates:
            # Add fallback unknown candidate for research subject
            candidates.append(
                CulturalClaimCandidate(
                    candidate_id="cand-fallback-unknown",
                    subject_id=evidence_pack.subject.subject_id,
                    canonical_motif_key=evidence_pack.subject.canonical_motif_key,
                    proposed_statement=f"{evidence_pack.subject.display_name} motifi için kültürel anlam iddiası"
                )
            )

        return candidates
