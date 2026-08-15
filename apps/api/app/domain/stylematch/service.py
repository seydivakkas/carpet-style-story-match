"""Service for Visual Style Match Engine."""
import uuid
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    UserPreferenceProfileModel,
    ImportanceProfileModel,
    PreferenceConfidenceProfileModel,
    UserProfileStatusEnum,
    VisualStyleMatchResultModel,
    VisualStyleMatchDimensionModel
)
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    StyleProfileStatus
)
from app.domain.preferences.exceptions import AssessmentNotFoundError
from app.domain.stylematch.constants import (
    VISUAL_STYLE_MATCH_VERSION,
    MATCH_LABEL_TR
)
from app.domain.stylematch.exceptions import (
    StyleMatchRequiresImportanceCompleteError,
    StyleMatchPreferenceProfileNotFoundError,
    StyleMatchImportanceProfileNotFoundError,
    StyleMatchCarpetProfileNotFoundError,
    StyleMatchCarpetProfileFailedError,
    StyleMatchNotFoundError
)
from app.domain.stylematch.schemas import (
    StyleMatchCreateRequest,
    StyleMatchDimensionResponse,
    StyleMatchExplanationResponse,
    VisualStyleMatchResultResponse
)
from app.domain.stylematch.engine import VisualStyleMatchEngine, CalculatedMatchResult
from app.domain.stylematch.repository import StyleMatchRepository

class StyleMatchService:
    """Service orchestrating Visual Style Match calculations and persistence."""

    @staticmethod
    def create_style_match(
        db: Session,
        assessment_id: uuid.UUID,
        payload: StyleMatchCreateRequest
    ) -> VisualStyleMatchResultResponse:
        assessment = (
            db.query(PreferenceAssessmentModel)
            .options(
                joinedload(PreferenceAssessmentModel.user_preference_profile).joinedload(UserPreferenceProfileModel.dimensions),
                joinedload(PreferenceAssessmentModel.importance_profile).joinedload(ImportanceProfileModel.dimensions),
                joinedload(PreferenceAssessmentModel.confidence_profile).joinedload(PreferenceConfidenceProfileModel.dimensions)
            )
            .filter(PreferenceAssessmentModel.id == assessment_id)
            .first()
        )
        if not assessment:
            raise AssessmentNotFoundError(assessment_id)

        # Precondition checks
        if not assessment.importance_profile:
            raise StyleMatchRequiresImportanceCompleteError(
                f"Assessment {assessment_id} importance profile must be complete to calculate style match."
            )

        user_pref_profile = assessment.user_preference_profile
        if not user_pref_profile or user_pref_profile.status != UserProfileStatusEnum.REVIEWED:
            raise StyleMatchPreferenceProfileNotFoundError(
                f"Assessment {assessment_id} does not have a reviewed user preference profile."
            )

        importance_profile = assessment.importance_profile

        # Load Carpet Style Profile
        carpet_profile = (
            db.query(CarpetStyleProfileModel)
            .options(joinedload(CarpetStyleProfileModel.dimensions))
            .filter(CarpetStyleProfileModel.id == payload.carpet_style_profile_id)
            .first()
        )
        if not carpet_profile:
            raise StyleMatchCarpetProfileNotFoundError(
                f"Carpet style profile {payload.carpet_style_profile_id} not found."
            )

        if carpet_profile.status == StyleProfileStatus.FAILED:
            raise StyleMatchCarpetProfileFailedError(
                f"Carpet style profile {payload.carpet_style_profile_id} status is FAILED."
            )

        # Idempotency check
        existing_match = StyleMatchRepository.get_existing(
            db=db,
            assessment_id=assessment_id,
            user_preference_profile_id=user_pref_profile.id,
            importance_profile_id=importance_profile.id,
            carpet_style_profile_id=carpet_profile.id,
            match_version=VISUAL_STYLE_MATCH_VERSION
        )
        if existing_match:
            return StyleMatchService._to_response(existing_match)

        # Extract dimension maps
        # 1. User preferences & confidence
        user_conf_map: Dict[str, float] = {}
        if assessment.confidence_profile and assessment.confidence_profile.dimensions:
            user_conf_map = {
                cd.dimension_key: float(cd.confidence) if cd.confidence is not None else 0.0
                for cd in assessment.confidence_profile.dimensions
            }

        user_dims_map: Dict[str, Dict[str, Any]] = {}
        for pd in user_pref_profile.dimensions:
            user_dims_map[pd.dimension_key] = {
                "final_value": pd.final_value,
                "provenance": pd.provenance,
                "status": pd.status.value if hasattr(pd.status, 'value') else str(pd.status),
                "confidence": user_conf_map.get(pd.dimension_key)
            }

        # 2. Importance
        imp_dims_map: Dict[str, Dict[str, Any]] = {}
        for idim in importance_profile.dimensions:
            imp_dims_map[idim.dimension_key] = {
                "level": idim.level,
                "weight": idim.weight
            }

        # 3. Carpet Style DNA
        carpet_dims_map: Dict[str, Dict[str, Any]] = {}
        for cdim in carpet_profile.dimensions:
            carpet_dims_map[cdim.dimension_key] = {
                "value": cdim.value,
                "status": cdim.status.value if hasattr(cdim.status, 'value') else str(cdim.status),
                "confidence": cdim.confidence
            }

        # Run Engine
        engine_result: CalculatedMatchResult = VisualStyleMatchEngine.compute_match(
            user_dimensions_map=user_dims_map,
            importance_dimensions_map=imp_dims_map,
            carpet_dimensions_map=carpet_dims_map
        )

        # Construct DB Models
        explanation_json_str = json.dumps(engine_result.explanation.model_dump())

        match_model = VisualStyleMatchResultModel(
            assessment_id=assessment_id,
            user_preference_profile_id=user_pref_profile.id,
            importance_profile_id=importance_profile.id,
            carpet_style_profile_id=carpet_profile.id,
            match_version=engine_result.match_version,
            status=engine_result.status,
            score=engine_result.score,
            score_100=engine_result.score_100,
            match_label=engine_result.match_label,
            comparable_dimension_count=engine_result.comparable_dimension_count,
            weighted_coverage=engine_result.weighted_coverage,
            total_importance_weight=engine_result.total_importance_weight,
            comparable_weight=engine_result.comparable_weight,
            explanation_json=explanation_json_str
        )

        for calc_dim in engine_result.dimensions:
            dim_model = VisualStyleMatchDimensionModel(
                dimension_key=calc_dim.dimension_key,
                user_value=calc_dim.user_value,
                user_provenance=calc_dim.user_provenance,
                carpet_value=calc_dim.carpet_value,
                carpet_dimension_status=calc_dim.carpet_dimension_status,
                importance_level=calc_dim.importance_level,
                importance_weight=calc_dim.importance_weight,
                difference=calc_dim.difference,
                similarity=calc_dim.similarity,
                weighted_similarity=calc_dim.weighted_similarity,
                weighted_difference=calc_dim.weighted_difference,
                comparable=calc_dim.comparable,
                user_preference_confidence=calc_dim.user_preference_confidence,
                carpet_measurement_confidence=calc_dim.carpet_measurement_confidence
            )
            match_model.dimensions.append(dim_model)

        saved_match = StyleMatchRepository.create(db, match_model)
        return StyleMatchService._to_response(saved_match)

    @staticmethod
    def get_style_match(
        db: Session,
        assessment_id: uuid.UUID,
        match_id: uuid.UUID
    ) -> VisualStyleMatchResultResponse:
        match_model = StyleMatchRepository.get_by_id(db, match_id)
        if not match_model or match_model.assessment_id != assessment_id:
            raise StyleMatchNotFoundError(f"Style match {match_id} not found for assessment {assessment_id}.")
        return StyleMatchService._to_response(match_model)

    @staticmethod
    def list_style_matches(
        db: Session,
        assessment_id: uuid.UUID
    ) -> List[VisualStyleMatchResultResponse]:
        matches = StyleMatchRepository.list_by_assessment(db, assessment_id)
        return [StyleMatchService._to_response(m) for m in matches]

    @staticmethod
    async def create_style_match_async(
        db: Any,
        assessment_id: uuid.UUID,
        payload: StyleMatchCreateRequest
    ) -> VisualStyleMatchResultResponse:
        if hasattr(db, "run_sync"):
            return await db.run_sync(
                lambda sync_session: StyleMatchService.create_style_match(
                    db=sync_session,
                    assessment_id=assessment_id,
                    payload=payload
                )
            )
        return StyleMatchService.create_style_match(db, assessment_id, payload)

    @staticmethod
    async def get_style_match_async(
        db: Any,
        assessment_id: uuid.UUID,
        match_id: uuid.UUID
    ) -> VisualStyleMatchResultResponse:
        if hasattr(db, "run_sync"):
            return await db.run_sync(
                lambda sync_session: StyleMatchService.get_style_match(
                    db=sync_session,
                    assessment_id=assessment_id,
                    match_id=match_id
                )
            )
        return StyleMatchService.get_style_match(db, assessment_id, match_id)

    @staticmethod
    async def list_style_matches_async(
        db: Any,
        assessment_id: uuid.UUID
    ) -> List[VisualStyleMatchResultResponse]:
        if hasattr(db, "run_sync"):
            return await db.run_sync(
                lambda sync_session: StyleMatchService.list_style_matches(
                    db=sync_session,
                    assessment_id=assessment_id
                )
            )
        return StyleMatchService.list_style_matches(db, assessment_id)

    @staticmethod
    def _to_response(model: VisualStyleMatchResultModel) -> VisualStyleMatchResultResponse:
        explanation_data = {}
        if model.explanation_json:
            try:
                explanation_data = json.loads(model.explanation_json)
            except Exception:
                explanation_data = {}

        explanation_resp = StyleMatchExplanationResponse(**explanation_data)

        match_label_tr = MATCH_LABEL_TR.get(model.match_label) if model.match_label else None

        dimension_responses = [
            StyleMatchDimensionResponse.model_validate(d) for d in model.dimensions
        ]

        return VisualStyleMatchResultResponse(
            id=model.id,
            assessment_id=model.assessment_id,
            user_preference_profile_id=model.user_preference_profile_id,
            importance_profile_id=model.importance_profile_id,
            carpet_style_profile_id=model.carpet_style_profile_id,
            match_version=model.match_version,
            status=model.status,
            score=model.score,
            score_100=model.score_100,
            match_label=model.match_label,
            match_label_tr=match_label_tr,
            comparable_dimension_count=model.comparable_dimension_count,
            weighted_coverage=model.weighted_coverage,
            total_importance_weight=model.total_importance_weight,
            comparable_weight=model.comparable_weight,
            dimensions=dimension_responses,
            explanation=explanation_resp,
            created_at=model.created_at
        )
