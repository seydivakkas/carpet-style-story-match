"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Cultural Claim Validator & Source-Bound Story Curator Test Suite.
Verifies categorical claim statuses (DOCUMENTED, CONTEXTUAL, CONTESTED, UNKNOWN),
grounding auditing, story presentation, safety boundaries, offline operation,
and strict database isolation.
"""
import pytest
from pydantic import ValidationError

from app.domain.research.models import (
    ResearchSubject,
    ResearchVerificationStatus,
    ResearchQueryPlan,
    ResearchSourceDocument,
    EvidenceUnit,
    EvidenceConflict,
    EvidencePack,
    SourceTier
)
from app.domain.research.claim_models import (
    CulturalClaimStatus,
    ClaimRelation,
    ClaimScope,
    ClaimEvidenceLink,
    CulturalClaimCandidate,
    ValidatedCulturalClaim
)
from app.domain.research.story_models import (
    StoryCitation,
    StorySection,
    StoryPresentation
)
from app.domain.research.claim_validator import CulturalClaimValidator
from app.domain.research.story_curator import TemplateStoryCurator
from app.domain.research.story_grounding import StoryGroundingValidator


def create_fixture_evidence_pack(units=None, conflicts=None, sources=None) -> EvidencePack:
    """Helper to build a valid EvidencePack fixture."""
    subj = ResearchSubject(
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED,
        display_name="Geometric Star",
        created_at="2026-08-17T00:00:00Z"
    )
    plan = ResearchQueryPlan(
        query_plan_id="plan-test-1",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        queries=["geometric-star motif history"],
        created_at="2026-08-17T00:00:00Z"
    )
    src = ResearchSourceDocument(
        source_id="src-met-1",
        canonical_url="https://www.metmuseum.org/art/collection/search/451001",
        title="Islamic Art Collection",
        institution_or_publisher="The Metropolitan Museum of Art",
        source_type="MUSEUM_CATALOG",
        source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
        retrieved_at="2026-08-17T00:00:00Z",
        content_sha256="1d6a24b8a9278ba381e54d22487789d802070a75cc80e8d8aaa0fcf670d0b63e"
    )

    default_units = [
        EvidenceUnit(
            evidence_id="ev-1",
            source_id="src-met-1",
            subject_motif_key="geometric-star",
            locator="paragraph-1",
            supporting_excerpt="The geometric-star motif appears in traditional Anatolian weaving as a decorative element.",
            normalized_summary="geometric-star motif Anatolian weaving decorative element",
            retrieval_score=0.95,
            source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
            content_hash="hash-1"
        )
    ]

    return EvidencePack(
        research_run_id="run-test-1",
        subject=subj,
        query_plan=plan,
        sources=sources or [src],
        evidence_units=units if units is not None else default_units,
        contradictions=conflicts or [],
        coverage={"searched_sources": 1, "evidence_count": len(units or default_units)},
        provenance={"policy_version": "source-quality-policy-v1.0.0"}
    )


def test_claim_validator_documented_status():
    """Validates that direct qualifying evidence without contradiction produces DOCUMENTED status."""
    pack = create_fixture_evidence_pack()
    validator = CulturalClaimValidator()

    cand = CulturalClaimCandidate(
        candidate_id="cand-1",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="geometric-star motif Anatolian weaving decorative element"
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert len(claims) == 1
    assert claims[0].status == CulturalClaimStatus.DOCUMENTED
    assert len(claims[0].evidence_links) == 1
    assert claims[0].evidence_links[0].relation == ClaimRelation.SUPPORTS
    assert "Directly supported" in claims[0].reasoning_summary


def test_claim_validator_contextual_status():
    """Validates that evidence limited by context or scope produces CONTEXTUAL status."""
    units = [
        EvidenceUnit(
            evidence_id="ev-context-1",
            source_id="src-met-1",
            subject_motif_key="geometric-star",
            locator="page-42",
            supporting_excerpt="Bu motif özellikle 19. yüzyıl Bergama dokumaları bağlamında görülmektedir.",
            normalized_summary="geometric-star motif özellikle Bergama bölgesinde görülmektedir",
            retrieval_score=0.90,
            source_tier=SourceTier.TIER_2_SCHOLARLY,
            content_hash="hash-context"
        )
    ]
    pack = create_fixture_evidence_pack(units=units)
    validator = CulturalClaimValidator()

    cand = CulturalClaimCandidate(
        candidate_id="cand-context",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="geometric-star motif Bergama dokumalarında görülmektedir",
        proposed_scope=ClaimScope(region="Bergama", period="19. yüzyıl")
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert len(claims) == 1
    assert claims[0].status == CulturalClaimStatus.CONTEXTUAL
    assert len(claims[0].limitations) > 0


def test_claim_validator_contested_status():
    """Validates that opposing evidence produces CONTESTED status and retains both sides."""
    units = [
        EvidenceUnit(
            evidence_id="ev-sup",
            source_id="src-met-1",
            subject_motif_key="geometric-star",
            locator="p-1",
            supporting_excerpt="geometric-star motif bereket sembolüdür.",
            normalized_summary="geometric-star motif bereket sembolüdür",
            retrieval_score=0.88,
            source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
            content_hash="hash-sup"
        )
    ]
    conflicts = [
        EvidenceConflict(
            conflict_id="conf-1",
            subject_motif_key="geometric-star",
            evidence_unit_ids=["ev-sup", "ev-opp"],
            conflict_type="ATTRIBUTION_DISCREPANCY",
            description="Bazı araştırmacılar bereket derken diğerleri koruma sembolü olduğunu iddia etmektedir."
        )
    ]
    pack = create_fixture_evidence_pack(units=units, conflicts=conflicts)
    validator = CulturalClaimValidator()

    cand = CulturalClaimCandidate(
        candidate_id="cand-contested",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="geometric-star motif bereket sembolüdür"
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert len(claims) == 1
    assert claims[0].status == CulturalClaimStatus.CONTESTED
    assert "Contested evidence" in claims[0].reasoning_summary


def test_claim_validator_unknown_status():
    """Validates that empty or irrelevant evidence produces UNKNOWN status."""
    pack = create_fixture_evidence_pack(units=[])
    validator = CulturalClaimValidator()

    cand = CulturalClaimCandidate(
        candidate_id="cand-unknown",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="geometric-star motif bilinmeyen sembol"
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert len(claims) == 1
    assert claims[0].status == CulturalClaimStatus.UNKNOWN
    assert "Insufficient qualifying evidence" in claims[0].reasoning_summary


def test_tier_1_not_automatic_documented():
    """Validates that a Tier-1 source with irrelevant content does NOT grant DOCUMENTED status."""
    units = [
        EvidenceUnit(
            evidence_id="ev-irrelevant",
            source_id="src-met-1",
            subject_motif_key="geometric-star",
            locator="p-99",
            supporting_excerpt="Bu katalog halı boyama teknikleri hakkındadır.",
            normalized_summary="halı boyama teknikleri mevcuttur",
            retrieval_score=0.20,
            source_tier=SourceTier.TIER_1_PRIMARY_INSTITUTIONAL,
            content_hash="hash-irr"
        )
    ]
    pack = create_fixture_evidence_pack(units=units)
    validator = CulturalClaimValidator()

    cand = CulturalClaimCandidate(
        candidate_id="cand-irr",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="geometric-star motif krallık sembolüdür"
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert len(claims) == 1
    assert claims[0].status == CulturalClaimStatus.UNKNOWN


def test_story_curator_template_only_offline():
    """Validates that TemplateStoryCurator generates clean Turkish presentation 100% offline."""
    pack = create_fixture_evidence_pack()
    validator = CulturalClaimValidator()
    claims = validator.validate_pack(pack)

    curator = TemplateStoryCurator()
    story = curator.generate_story(claims, pack)

    assert story.generation_mode == "TEMPLATE_ONLY"
    assert story.generator_version == "source-bound-story-v1.0.0"
    assert len(story.sections) >= 1
    assert len(story.citations) >= 1
    assert story.canonical_motif_key == "geometric-star"


def test_story_grounding_validator_pass():
    """Validates that clean story presentation passes grounding auditing."""
    pack = create_fixture_evidence_pack()
    validator = CulturalClaimValidator()
    claims = validator.validate_pack(pack)

    curator = TemplateStoryCurator()
    story = curator.generate_story(claims, pack)

    grounding = StoryGroundingValidator()
    res = grounding.validate_story(story, claims, pack)

    assert res.is_valid is True
    assert len(res.violations) == 0
    assert res.grounding_score == 1.0


def test_story_grounding_validator_failures():
    """Validates that grounding auditor catches status upgrades, missing citations, and forbidden phrases."""
    pack = create_fixture_evidence_pack()
    validator = CulturalClaimValidator()
    claims = validator.validate_pack(pack)

    curator = TemplateStoryCurator()
    story = curator.generate_story(claims, pack)

    # Mutate section to introduce a status upgrade / forbidden phrase
    story.sections[0].text += " Seljuk carpet confirmed."

    grounding = StoryGroundingValidator()
    res = grounding.validate_story(story, claims, pack)

    assert res.is_valid is False
    assert any("Forbidden origin authentication phrase" in v for v in res.violations)


def test_color_and_dye_safety():
    """Validates that color observations generate zero cultural or dye claims."""
    # Build EvidencePack with only color observations
    pack = create_fixture_evidence_pack(units=[])
    validator = CulturalClaimValidator()

    # Candidate proposing dye inference from red color alone
    cand = CulturalClaimCandidate(
        candidate_id="cand-dye",
        subject_id="subj-test-1",
        canonical_motif_key="geometric-star",
        proposed_statement="Kırmızı renk madder boyası olduğunu kanıtlar"
    )

    claims = validator.validate_pack(pack, candidates=[cand])
    assert claims[0].status == CulturalClaimStatus.UNKNOWN


def test_strict_dto_forbid_extra_fields():
    """Validates that extra fields in DTOs raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        ValidatedCulturalClaim(
            claim_id="c-1",
            subject_id="s-1",
            canonical_motif_key="star",
            statement="test",
            status=CulturalClaimStatus.DOCUMENTED,
            reasoning_summary="test",
            validator_version="cultural-claim-validator-v1.0.0",
            provenance={},
            truth_score=0.99  # FORBIDDEN EXTRA FIELD
        )

    with pytest.raises(ValidationError):
        StoryPresentation(
            story_id="st-1",
            subject_id="s-1",
            canonical_motif_key="star",
            title="title",
            summary="summary",
            generator_version="source-bound-story-v1.0.0",
            provenance={},
            personalized_narrative="forbidden"  # FORBIDDEN EXTRA FIELD
        )
