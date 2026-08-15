import uuid
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.preferences.service import PreferenceAssessmentService
from app.domain.preferences.schemas import (
    PreferenceAssessmentRead,
    TextResponseCreate,
    TextResponseRead,
    TextPreferenceProfileRead,
    VisualPresentationRead,
    VisualResponseCreate,
    VisualResponseRead,
    VisualPreferenceProfileRead,
    DimensionOverrideRequest,
    UserPreferenceProfileResponse,
    PreferenceConfidenceProfileResponse,
    ImportanceSelectionRequest,
    ImportanceProfileResponse
)
from app.domain.preferences.exceptions import (
    AssessmentNotFoundError,
    TextPreferencesIncompleteError,
    TextPreferencesAlreadyCompletedError,
    InvalidQuestionKeyError,
    VisualPhaseRequiresTextCompleteError,
    VisualPreferencesIncompleteError,
    VisualPreferencesAlreadyCompletedError,
    InvalidStimulusKeyError,
    VisualProfileNotFoundError,
    MultimodalProfileRequiresVisualCompleteError,
    PreferenceProfileNotFoundError,
    PreferenceConfidenceProfileNotFoundError,
    PreferenceDimensionNotFoundError,
    PreferenceValueError,
    PreferenceProfileAlreadyReviewedError,
    ImportanceRequiresReviewedPreferenceProfileError,
    ImportanceSelectionTooManyPriorityError,
    ImportanceSelectionTooManyFlexibleError,
    ImportanceSelectionOverlapError,
    ImportanceSelectionDuplicateError,
    ImportanceSelectionUnknownDimensionError,
    ImportanceSelectionInvalidSkipError,
    ImportanceSelectionEmptyError,
    ImportanceProfileAlreadyExistsError,
    ImportanceProfileNotFoundError
)

router = APIRouter(prefix="", tags=["Preference Assessments"])

def get_service(db: AsyncSession = Depends(get_db)) -> PreferenceAssessmentService:
    return PreferenceAssessmentService(db)

def build_presentation_read(p) -> VisualPresentationRead:
    left_url = f"/api/v1/preference-stimuli/{p.stimulus_version}/{p.stimulus_key.lower()}_{p.left_variant.lower()}.svg"
    right_url = f"/api/v1/preference-stimuli/{p.stimulus_version}/{p.stimulus_key.lower()}_{p.right_variant.lower()}.svg"
    return VisualPresentationRead(
        id=p.id,
        assessment_id=p.assessment_id,
        stimulus_key=p.stimulus_key,
        left_asset_url=left_url,
        right_asset_url=right_url
    )

# ---------------------------------------------------------
# TEXT PREFERENCE ASSESSMENT ENDPOINTS
# ---------------------------------------------------------

@router.post(
    "/preference-assessments",
    response_model=PreferenceAssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new anonymous Preference Assessment"
)
async def create_assessment(service: PreferenceAssessmentService = Depends(get_service)):
    return await service.create_assessment()

@router.get(
    "/preference-assessments/{assessment_id}",
    response_model=PreferenceAssessmentRead,
    status_code=status.HTTP_200_OK,
    summary="Get Preference Assessment status"
)
async def get_assessment(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_assessment(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.put(
    "/preference-assessments/{assessment_id}/text-responses/{question_key}",
    response_model=TextResponseRead,
    status_code=status.HTTP_200_OK,
    summary="Upsert user choice for a text preference question"
)
async def save_text_response(
    assessment_id: uuid.UUID,
    question_key: str,
    payload: TextResponseCreate,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.save_text_response(assessment_id, question_key, payload.choice)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except InvalidQuestionKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVALID_QUESTION_KEY", "message": str(exc)}
        ) from exc
    except TextPreferencesAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "TEXT_PREFERENCES_ALREADY_COMPLETED", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/text-responses",
    response_model=List[TextResponseRead],
    status_code=status.HTTP_200_OK,
    summary="Get answered text preference responses"
)
async def get_text_responses(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_text_responses(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.post(
    "/preference-assessments/{assessment_id}/complete-text",
    response_model=TextPreferenceProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Complete text preference assessment and generate Text Preference Profile"
)
async def complete_text_assessment(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.complete_text_assessment(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except TextPreferencesIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TEXT_PREFERENCES_INCOMPLETE",
                "message": str(exc),
                "answered_count": exc.answered_count,
                "missing_keys": exc.missing_keys
            }
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/text-profile",
    response_model=TextPreferenceProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get calculated Text Preference Profile"
)
async def get_text_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_text_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except TextPreferencesIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TEXT_PREFERENCES_INCOMPLETE",
                "message": str(exc),
                "answered_count": exc.answered_count,
                "missing_keys": exc.missing_keys
            }
        ) from exc

# ---------------------------------------------------------
# VISUAL PREFERENCE ASSESSMENT ENDPOINTS (GÖREV 05)
# ---------------------------------------------------------

@router.post(
    "/preference-assessments/{assessment_id}/start-visual",
    response_model=List[VisualPresentationRead],
    status_code=status.HTTP_200_OK,
    summary="Start visual preference phase and generate side-randomized presentations"
)
async def start_visual_phase(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        presentations = await service.start_visual_phase(assessment_id)
        return [build_presentation_read(p) for p in presentations]
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except VisualPhaseRequiresTextCompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "VISUAL_PHASE_REQUIRES_TEXT_COMPLETE", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/visual-presentations",
    response_model=List[VisualPresentationRead],
    status_code=status.HTTP_200_OK,
    summary="Get visual preference card presentations in canonical order"
)
async def get_visual_presentations(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        presentations = await service.get_visual_presentations(assessment_id)
        return [build_presentation_read(p) for p in presentations]
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.put(
    "/preference-assessments/{assessment_id}/visual-responses/{stimulus_key}",
    response_model=VisualResponseRead,
    status_code=status.HTTP_200_OK,
    summary="Save display choice for a visual preference card"
)
async def save_visual_response(
    assessment_id: uuid.UUID,
    stimulus_key: str,
    payload: VisualResponseCreate,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.save_visual_response(assessment_id, stimulus_key, payload.choice)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except InvalidStimulusKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVALID_STIMULUS_KEY", "message": str(exc)}
        ) from exc
    except VisualPreferencesAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "VISUAL_PREFERENCES_ALREADY_COMPLETED", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/visual-responses",
    response_model=List[VisualResponseRead],
    status_code=status.HTTP_200_OK,
    summary="Get answered visual preference responses"
)
async def get_visual_responses(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_visual_responses(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.post(
    "/preference-assessments/{assessment_id}/complete-visual",
    response_model=VisualPreferenceProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Complete visual preference assessment and generate Visual Preference Profile"
)
async def complete_visual_assessment(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.complete_visual_assessment(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except VisualPreferencesIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VISUAL_PREFERENCES_INCOMPLETE",
                "message": str(exc),
                "answered_count": exc.answered_count,
                "missing_keys": exc.missing_keys
            }
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/visual-profile",
    response_model=VisualPreferenceProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get calculated Visual Preference Profile"
)
async def get_visual_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_visual_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except VisualProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VISUAL_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc

# ---------------------------------------------------------
# MULTIMODAL PREFERENCE PROFILE ENDPOINTS (GÖREV 06)
# ---------------------------------------------------------

@router.post(
    "/preference-assessments/{assessment_id}/build-profile",
    response_model=UserPreferenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Build multimodal 9D User Preference Profile and Confidence Profile"
)
async def build_multimodal_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.build_multimodal_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except MultimodalProfileRequiresVisualCompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "MULTIMODAL_PROFILE_REQUIRES_VISUAL_COMPLETE", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/preference-profile",
    response_model=UserPreferenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get calculated User Preference Profile"
)
async def get_user_preference_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_user_preference_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREFERENCE_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/confidence-profile",
    response_model=PreferenceConfidenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get calculated Preference Confidence Profile"
)
async def get_confidence_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_confidence_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceConfidenceProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREFERENCE_CONFIDENCE_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc

@router.put(
    "/preference-assessments/{assessment_id}/preference-profile/dimensions/{dimension_key}",
    response_model=UserPreferenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="User override of a single preference dimension value"
)
async def override_preference_dimension(
    assessment_id: uuid.UUID,
    dimension_key: str,
    payload: DimensionOverrideRequest,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.override_user_preference_dimension(
            assessment_id=assessment_id,
            dimension_key=dimension_key,
            value=payload.value
        )
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREFERENCE_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceDimensionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREFERENCE_DIMENSION_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PREFERENCE_VALUE_OUT_OF_RANGE", "message": str(exc)}
        ) from exc
    except PreferenceProfileAlreadyReviewedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PREFERENCE_PROFILE_ALREADY_REVIEWED", "message": str(exc)}
        ) from exc

@router.post(
    "/preference-assessments/{assessment_id}/confirm-profile",
    response_model=UserPreferenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm preference profile review"
)
async def confirm_user_preference_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.confirm_user_preference_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except PreferenceProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PREFERENCE_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc

# ---------------------------------------------------------
# IMPORTANCE PROFILE ENDPOINTS (GÖREV 07)
# ---------------------------------------------------------

@router.post(
    "/preference-assessments/{assessment_id}/importance-profile",
    response_model=ImportanceProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create explicit Importance Profile for reviewed assessment"
)
async def create_importance_profile(
    assessment_id: uuid.UUID,
    payload: ImportanceSelectionRequest,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.create_importance_profile(
            assessment_id=assessment_id,
            skip=payload.skip,
            priority_dimensions=payload.priority_dimensions,
            flexible_dimensions=payload.flexible_dimensions
        )
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except ImportanceRequiresReviewedPreferenceProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "IMPORTANCE_REQUIRES_REVIEWED_PREFERENCE_PROFILE", "message": str(exc)}
        ) from exc
    except ImportanceSelectionTooManyPriorityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_TOO_MANY_PRIORITY", "message": str(exc)}
        ) from exc
    except ImportanceSelectionTooManyFlexibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_TOO_MANY_FLEXIBLE", "message": str(exc)}
        ) from exc
    except ImportanceSelectionOverlapError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_SELECTION_OVERLAP", "message": str(exc)}
        ) from exc
    except ImportanceSelectionDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_SELECTION_DUPLICATE", "message": str(exc)}
        ) from exc
    except ImportanceSelectionUnknownDimensionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_SELECTION_UNKNOWN_DIMENSION", "message": str(exc)}
        ) from exc
    except ImportanceSelectionInvalidSkipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_SELECTION_INVALID_SKIP", "message": str(exc)}
        ) from exc
    except ImportanceSelectionEmptyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMPORTANCE_SELECTION_EMPTY", "message": str(exc)}
        ) from exc
    except ImportanceProfileAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "IMPORTANCE_PROFILE_ALREADY_EXISTS", "message": str(exc)}
        ) from exc

@router.get(
    "/preference-assessments/{assessment_id}/importance-profile",
    response_model=ImportanceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Importance Profile for assessment"
)
async def get_importance_profile(
    assessment_id: uuid.UUID,
    service: PreferenceAssessmentService = Depends(get_service)
):
    try:
        return await service.get_importance_profile(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSESSMENT_NOT_FOUND", "message": str(exc)}
        ) from exc
    except ImportanceProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "IMPORTANCE_PROFILE_NOT_FOUND", "message": str(exc)}
        ) from exc

# ---------------------------------------------------------
# STIMULUS ASSET SERVING ENDPOINT
# ---------------------------------------------------------

STIMULI_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "stimuli")

@router.get(
    "/preference-stimuli/{version}/{filename}",
    status_code=status.HTTP_200_OK,
    summary="Serve static visual preference stimulus asset"
)
async def get_preference_stimulus_asset(version: str, filename: str):
    # Path traversal prevention
    clean_ver = os.path.basename(version)
    clean_filename = os.path.basename(filename)

    if not clean_filename.endswith((".svg", ".png")):
        raise HTTPException(status_code=400, detail="Invalid asset extension")

    file_path = os.path.join(STIMULI_STATIC_DIR, clean_ver, clean_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stimulus asset not found")

    media_type = "image/svg+xml" if clean_filename.endswith(".svg") else "image/png"
    return FileResponse(file_path, media_type=media_type)
