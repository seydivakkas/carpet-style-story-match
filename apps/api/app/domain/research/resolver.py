"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Canonical Motif & Alias Resolver.
Strict controlled registry mapping user/CLI inputs to canonical motifs.
Forbids arbitrary free-text strings from becoming VERIFIED_CANONICAL research subjects.
"""
from typing import Optional, Dict, Any, Tuple
from app.domain.research.models import ResearchSubject, ResearchVerificationStatus

CANONICAL_MOTIFS = {
    "medallion",
    "mihrab",
    "palmette",
    "lotus",
    "rosette",
    "cloud-band",
    "scrolling-vine",
    "geometric-star",
    "ram-horn",
    "tree-of-life",
    "elibelinde",
    "comb",
    "mystery-hook"
}

APPROVED_MOTIF_ALIASES: Dict[str, str] = {
    "star": "geometric-star",
    "geometric_star": "geometric-star",
    "eight_pointed_star": "geometric-star",
    "eight-pointed-star": "geometric-star",
    "tree": "tree-of-life",
    "tree_of_life": "tree-of-life",
    "cloud_band": "cloud-band",
    "scrolling_vine": "scrolling-vine",
    "ram_horn": "ram-horn",
    "hands_on_hips": "elibelinde",
    "hook": "mystery-hook",
    "mystery_hook": "mystery-hook"
}


def resolve_canonical_motif_subject(
    motif_input: str,
    caller_verification_status: Optional[ResearchVerificationStatus] = None
) -> ResearchSubject:
    """
    Resolves an input string or alias against the controlled canonical motif registry.
    
    Raises:
        ValueError("UNKNOWN_MOTIF"): if input is not in canonical set or approved alias registry.
        ValueError("BLOCKED"): if verification status is unverified (AI_CANDIDATE, UNMAPPED, ABSTAINED).
    """
    if not motif_input or not isinstance(motif_input, str):
        raise ValueError("UNKNOWN_MOTIF: Empty or non-string motif input provided.")

    cleaned_input = motif_input.strip().lower()

    # 1. Verification status check if explicitly provided
    if caller_verification_status in (
        ResearchVerificationStatus.AI_CANDIDATE,
        ResearchVerificationStatus.UNMAPPED_MOTIF_CANDIDATE,
        ResearchVerificationStatus.ABSTAINED
    ):
        raise ValueError(
            f"BLOCKED for unverified motif candidates (status={caller_verification_status.value if hasattr(caller_verification_status, 'value') else caller_verification_status}). "
            "Verification state is mandatory for cultural research."
        )

    # 2. Canonical Resolution
    resolved_key: Optional[str] = None
    mechanism: str = ""

    if cleaned_input in CANONICAL_MOTIFS:
        resolved_key = cleaned_input
        mechanism = "EXACT_CANONICAL_MATCH"
    elif cleaned_input in APPROVED_MOTIF_ALIASES:
        resolved_key = APPROVED_MOTIF_ALIASES[cleaned_input]
        mechanism = "CURATED_ALIAS_REGISTRY"
    else:
        raise ValueError(
            f"UNKNOWN_MOTIF: '{motif_input}' is not a recognized canonical motif key or registered alias. "
            "Arbitrary free-text queries cannot bypass controlled verification."
        )

    # Determine final verification status
    v_status = caller_verification_status or ResearchVerificationStatus.CURATOR_CONFIRMED

    display_name = resolved_key.replace("-", " ").replace("_", " ").title()

    from datetime import datetime, timezone
    return ResearchSubject(
        subject_id=f"subj-resolved-{resolved_key}",
        canonical_motif_key=resolved_key,
        verification_status=v_status,
        display_name=display_name,
        ontology_version="motif-ontology-v1.0.0",
        known_source_context={
            "input_alias": motif_input,
            "resolved_canonical_key": resolved_key,
            "resolution_mechanism": mechanism,
            "verification_source": "ControlledOntologyRegistry"
        },
        created_at=datetime.now(timezone.utc).isoformat()
    )


def resolve_research_subject_from_review(
    review_subject_id: str,
    db: Any
) -> ResearchSubject:
    """
    Resolves a ResearchSubject from a persisted MotifReviewSubject by evaluating its effective human review state.
    
    Returns trusted ResearchSubject if effective status == CURATOR_CONFIRMED.
    Raises ValueError("BLOCKED") if pending, UNCERTAIN, or REJECTED.
    """
    from app.domain.motif_review.repository import MotifReviewRepository
    subject_model = MotifReviewRepository.get_subject_by_public_id(db, review_subject_id)
    if subject_model is None:
        raise KeyError(f"Review subject '{review_subject_id}' not found.")

    latest_event = MotifReviewRepository.get_effective_event(db, subject_model.id)
    if latest_event is None or latest_event.resulting_status != "CURATOR_CONFIRMED":
        status_str = latest_event.resulting_status if latest_event else "PENDING"
        raise ValueError(
            f"BLOCKED: Review subject '{review_subject_id}' is not CURATOR_CONFIRMED (status={status_str})."
        )

    canonical_key = latest_event.selected_canonical_motif_key or subject_model.proposed_canonical_motif_key
    if not canonical_key:
        raise ValueError(f"BLOCKED: Confirmed review subject '{review_subject_id}' missing canonical motif key.")

    return resolve_canonical_motif_subject(
        motif_input=canonical_key,
        caller_verification_status=ResearchVerificationStatus.CURATOR_CONFIRMED
    )

