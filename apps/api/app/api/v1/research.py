"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Source Research API Router.
Provides endpoints for evidence pack retrieval and research provider status.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.research import (
    ResearchSubject,
    ResearchVerificationStatus,
    EvidencePack,
    SourceResearchService,
    EVIDENCE_PACK_SCHEMA_VERSION,
    RESEARCH_QUERY_PLAN_VERSION,
    ValidatedCulturalClaim,
    CulturalClaimValidator,
    StoryPresentation,
    TemplateStoryCurator,
    StoryGroundingValidator,
    CULTURAL_CLAIM_SCHEMA_VERSION,
    CULTURAL_CLAIM_VALIDATOR_VERSION,
    SOURCE_BOUND_STORY_SCHEMA_VERSION,
    STORY_GROUNDING_POLICY_VERSION
)

router = APIRouter(prefix="/research", tags=["Source Research Engine"])


class ResearchSubjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_motif_key: str = Field(..., description="Canonical motif key e.g. 'star', 'tree-of-life', 'medallion'")
    display_name: Optional[str] = None
    verification_status: ResearchVerificationStatus = Field(
        default=ResearchVerificationStatus.CURATOR_CONFIRMED,
        description="Must be CURATOR_CONFIRMED or VERIFIED_CANONICAL"
    )
    direct_url: Optional[str] = Field(None, description="Optional approved direct official URL to fetch")


class ClaimStoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ValidatedCulturalClaim] = Field(..., description="Validated cultural claims input")
    evidence_pack: EvidencePack = Field(..., description="Frozen EvidencePack input")


@router.post(
    "/evidence-pack",
    response_model=EvidencePack,
    status_code=status.HTTP_200_OK,
    summary="Execute evidence RAG search for a verified motif subject"
)
async def generate_evidence_pack(
    req: ResearchSubjectRequest,
    db: AsyncSession = Depends(get_db)
) -> EvidencePack:
    # 1. INPUT GATE CHECK: Unverified candidates are strictly blocked
    if req.verification_status not in {ResearchVerificationStatus.CURATOR_CONFIRMED, ResearchVerificationStatus.VERIFIED_CANONICAL}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Research is BLOCKED for unverified candidates ({req.verification_status.value}). Subject must be CURATOR_CONFIRMED or VERIFIED_CANONICAL."
        )

    disp_name = req.display_name or req.canonical_motif_key.replace("_", " ").replace("-", " ").title()
    subject_id = f"subj-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    subject = ResearchSubject(
        subject_id=subject_id,
        canonical_motif_key=req.canonical_motif_key,
        verification_status=req.verification_status,
        display_name=disp_name,
        created_at=timestamp
    )

    service = SourceResearchService(db_session=db)
    try:
        pack = await service.execute_research(subject, direct_url=req.direct_url)
        return pack
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Research service error: {e}")


@router.post(
    "/validate-claims",
    response_model=list[ValidatedCulturalClaim],
    status_code=status.HTTP_200_OK,
    summary="Validate cultural claims strictly against EvidencePack evidence"
)
async def validate_claims(
    pack: EvidencePack
) -> list[ValidatedCulturalClaim]:
    validator = CulturalClaimValidator()
    try:
        validated = validator.validate_pack(pack)
        return validated
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Claim validation error: {e}")


@router.post(
    "/story",
    response_model=StoryPresentation,
    status_code=status.HTTP_200_OK,
    summary="Generate source-bound story presentation strictly from validated claims"
)
async def generate_story(
    req: ClaimStoryRequest
) -> StoryPresentation:
    curator = TemplateStoryCurator()
    grounding = StoryGroundingValidator()
    try:
        story = curator.generate_story(req.claims, req.evidence_pack)
        res = grounding.validate_story(story, req.claims, req.evidence_pack)
        if not res.is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Story failed grounding audit: {res.violations}"
            )
        return story
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Story generation error: {e}")


@router.post(
    "/narrative",
    status_code=status.HTTP_200_OK,
    summary="Composed pipeline: EvidencePack -> Validated Claims -> Source-Bound Story"
)
async def generate_narrative_pipeline(
    req: ResearchSubjectRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    pack = await generate_evidence_pack(req, db)
    claims = await validate_claims(pack)
    story = await generate_story(ClaimStoryRequest(claims=claims, evidence_pack=pack))
    return {
        "evidence_pack": pack,
        "validated_claims": claims,
        "story": story
    }


@router.get(
    "/provider-status",
    status_code=status.HTTP_200_OK,
    summary="Get source research engine provider and policy status"
)
async def get_research_provider_status() -> Dict[str, Any]:
    return {
        "status": "HEALTHY",
        "query_plan_version": RESEARCH_QUERY_PLAN_VERSION,
        "evidence_pack_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "source_quality_policy_version": "source-quality-policy-v1.0.0",
        "cultural_claim_schema_version": CULTURAL_CLAIM_SCHEMA_VERSION,
        "cultural_claim_validator_version": CULTURAL_CLAIM_VALIDATOR_VERSION,
        "source_bound_story_schema_version": SOURCE_BOUND_STORY_SCHEMA_VERSION,
        "story_grounding_policy_version": STORY_GROUNDING_POLICY_VERSION,
        "providers": {
            "curated_corpus": "ACTIVE",
            "direct_official": "ACTIVE",
            "remote_search": "DISABLED",
            "story_template": "ACTIVE",
            "story_model": "NOT_CONFIGURED"
        }
    }

