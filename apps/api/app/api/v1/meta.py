from fastapi import APIRouter
from app.domain.contracts import (
    CANONICAL_STYLE_DNA,
    CANONICAL_NARRATIVE_THEMES,
    StyleDNAContractResponse,
    NarrativeThemesContractResponse
)

router = APIRouter(prefix="/meta", tags=["metadata"])

@router.get("/style-dna", response_model=StyleDNAContractResponse)
async def get_style_dna_metadata():
    return StyleDNAContractResponse(
        total_dimensions=len(CANONICAL_STYLE_DNA),
        dimensions=CANONICAL_STYLE_DNA
    )

@router.get("/narrative-themes", response_model=NarrativeThemesContractResponse)
async def get_narrative_themes_metadata():
    return NarrativeThemesContractResponse(
        total_themes=len(CANONICAL_NARRATIVE_THEMES),
        themes=CANONICAL_NARRATIVE_THEMES
    )
