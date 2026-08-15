from fastapi import APIRouter
from app.domain.contracts import (
    CANONICAL_STYLE_DNA,
    CANONICAL_NARRATIVE_THEMES,
    StyleDNAContractResponse,
    NarrativeThemesContractResponse
)
from app.domain.preferences.constants import CANONICAL_TEXT_QUESTIONS
from app.domain.preferences.visual_stimuli import STIMULI_CATALOG, CANONICAL_VISUAL_CARDS
from app.domain.preferences.schemas import (
    TextQuestionsListResponse,
    TextQuestionRead,
    VisualStimuliListResponse,
    VisualStimulusRead
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

@router.get("/preference-text-questions", response_model=TextQuestionsListResponse)
async def get_preference_text_questions_metadata():
    return TextQuestionsListResponse(
        total_questions=len(CANONICAL_TEXT_QUESTIONS),
        questions=[TextQuestionRead(**q) for q in CANONICAL_TEXT_QUESTIONS]
    )

@router.get("/preference-visual-stimuli", response_model=VisualStimuliListResponse)
async def get_preference_visual_stimuli_metadata():
    stimuli_list = [
        VisualStimulusRead(
            stimulus_key=key,
            target_dimension=STIMULI_CATALOG[key]["target_dimension"],
            base_family=STIMULI_CATALOG[key]["base_family"],
            description=STIMULI_CATALOG[key]["description"]
        )
        for key in CANONICAL_VISUAL_CARDS
    ]
    return VisualStimuliListResponse(
        total_stimuli=len(stimuli_list),
        stimuli=stimuli_list
    )
