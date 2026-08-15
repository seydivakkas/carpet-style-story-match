import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.preferences.service import PreferenceAssessmentService
from app.domain.preferences.schemas import (
    PreferenceAssessmentRead,
    TextResponseCreate,
    TextResponseRead,
    TextPreferenceProfileRead
)
from app.domain.preferences.exceptions import (
    AssessmentNotFoundError,
    TextPreferencesIncompleteError,
    TextPreferencesAlreadyCompletedError,
    InvalidQuestionKeyError
)

router = APIRouter(prefix="/preference-assessments", tags=["Preference Assessments"])

def get_service(db: AsyncSession = Depends(get_db)) -> PreferenceAssessmentService:
    return PreferenceAssessmentService(db)

@router.post(
    "",
    response_model=PreferenceAssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new anonymous Preference Assessment"
)
async def create_assessment(service: PreferenceAssessmentService = Depends(get_service)):
    return await service.create_assessment()

@router.get(
    "/{assessment_id}",
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
    "/{assessment_id}/text-responses/{question_key}",
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
    "/{assessment_id}/text-responses",
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
    "/{assessment_id}/complete-text",
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
    "/{assessment_id}/text-profile",
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
