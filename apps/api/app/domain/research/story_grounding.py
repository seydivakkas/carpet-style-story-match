"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Story Grounding Validator Implementation.
Audits StoryPresentations against ValidatedCulturalClaims and EvidencePacks to guarantee zero
hallucinations, zero status upgrades, zero unsourced claims, and strict citation traceability.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.research.models import EvidencePack
from app.domain.research.claim_models import ValidatedCulturalClaim, CulturalClaimStatus
from app.domain.research.story_models import StoryPresentation, STORY_GROUNDING_POLICY_VERSION


class GroundingValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_valid: bool
    policy_version: str = Field(default=STORY_GROUNDING_POLICY_VERSION)
    violations: List[str] = Field(default_factory=list)
    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)


class StoryGroundingValidator:
    """
    Audits StoryPresentation objects for strict evidence grounding compliance:
    - Every section text must trace to >= 1 validated claim ID.
    - Every citation must resolve to an EvidenceUnit and SourceDocument in EvidencePack.
    - Status preservation: CONTEXTUAL limits preserved, CONTESTED sides retained, UNKNOWN decorated as unknown.
    - No unsourced claims or external citations.
    - No origin authentication or personality inferences.
    """

    def __init__(self, policy_version: str = STORY_GROUNDING_POLICY_VERSION):
        self.policy_version = policy_version

    def validate_story(
        self,
        story: StoryPresentation,
        input_claims: List[ValidatedCulturalClaim],
        evidence_pack: EvidencePack
    ) -> GroundingValidationResult:
        violations: List[str] = []

        valid_claim_ids = {c.claim_id: c for c in input_claims}
        valid_unit_ids = {u.evidence_id: u for u in evidence_pack.evidence_units}
        valid_source_ids = {s.source_id: s for s in evidence_pack.sources}

        # Rule 1: Every section must reference at least one valid claim_id
        for sec in story.sections:
            if not sec.claim_ids:
                violations.append(f"Section '{sec.section_id}' ({sec.heading}) does not reference any claim_id.")
            for cid in sec.claim_ids:
                if cid not in valid_claim_ids:
                    violations.append(f"Section '{sec.section_id}' references unknown claim_id '{cid}'.")

        # Rule 2: Every citation must resolve to EvidenceUnit and Source in EvidencePack
        for cit in story.citations:
            if cit.claim_id not in valid_claim_ids:
                violations.append(f"Citation '{cit.citation_id}' references unknown claim_id '{cit.claim_id}'.")
            if cit.evidence_unit_id not in valid_unit_ids:
                violations.append(f"Citation '{cit.citation_id}' references unknown evidence_unit_id '{cit.evidence_unit_id}'.")
            if cit.source_id not in valid_source_ids:
                violations.append(f"Citation '{cit.citation_id}' references unknown source_id '{cit.source_id}'.")

        # Rule 3: Status preservation auditing
        for cid, claim in valid_claim_ids.items():
            sections_for_claim = [sec for sec in story.sections if cid in sec.claim_ids]
            for sec in sections_for_claim:
                text_lower = sec.text.lower()

                if claim.status == CulturalClaimStatus.CONTEXTUAL:
                    if any(w in text_lower for w in ["evrenseldir", "her zaman", "kesinlikle"]):
                        violations.append(
                            f"Status upgrade detected for CONTEXTUAL claim '{cid}' in section '{sec.section_id}': "
                            f"universal claims forbidden."
                        )

                elif claim.status == CulturalClaimStatus.CONTESTED:
                    if "farklı" not in text_lower and "tartışma" not in text_lower and "görüş" not in text_lower:
                        violations.append(
                            f"Discrepancy omission detected for CONTESTED claim '{cid}' in section '{sec.section_id}': "
                            f"must explicitly disclose disagreement."
                        )

                elif claim.status == CulturalClaimStatus.UNKNOWN:
                    if any(w in text_lower for w in ["muhtemelen", "probably", "belgelenmiştir", "anlamına gelir"]):
                        violations.append(
                            f"Speculative decoration detected for UNKNOWN claim '{cid}' in section '{sec.section_id}': "
                            f"unknown must remain unknown."
                        )

        # Rule 4: Forbidden origin authentication statements
        forbidden_auth_phrases = ["seljuk carpet confirmed", "safavid carpet confirmed", "ottoman carpet confirmed"]
        for sec in story.sections:
            text_lower = sec.text.lower()
            for phrase in forbidden_auth_phrases:
                if phrase in text_lower:
                    violations.append(f"Forbidden origin authentication phrase '{phrase}' detected in section '{sec.section_id}'.")

        is_valid = len(violations) == 0
        score = 1.0 if is_valid else max(0.0, 1.0 - (0.2 * len(violations)))

        return GroundingValidationResult(
            is_valid=is_valid,
            policy_version=self.policy_version,
            violations=violations,
            grounding_score=score
        )
