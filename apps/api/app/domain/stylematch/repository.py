"""Repository for Visual Style Match Engine."""
import uuid
import json
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.db.models.preference_assessment import (
    VisualStyleMatchResultModel,
    VisualStyleMatchDimensionModel
)
from app.domain.stylematch.constants import VISUAL_STYLE_MATCH_VERSION

class StyleMatchRepository:
    """Repository managing Visual Style Match DB operations."""

    @staticmethod
    def get_by_id(db: Session, match_id: uuid.UUID) -> Optional[VisualStyleMatchResultModel]:
        return (
            db.query(VisualStyleMatchResultModel)
            .options(joinedload(VisualStyleMatchResultModel.dimensions))
            .filter(VisualStyleMatchResultModel.id == match_id)
            .first()
        )

    @staticmethod
    def get_existing(
        db: Session,
        assessment_id: uuid.UUID,
        user_preference_profile_id: uuid.UUID,
        importance_profile_id: uuid.UUID,
        carpet_style_profile_id: uuid.UUID,
        match_version: str = VISUAL_STYLE_MATCH_VERSION
    ) -> Optional[VisualStyleMatchResultModel]:
        return (
            db.query(VisualStyleMatchResultModel)
            .options(joinedload(VisualStyleMatchResultModel.dimensions))
            .filter(
                VisualStyleMatchResultModel.assessment_id == assessment_id,
                VisualStyleMatchResultModel.user_preference_profile_id == user_preference_profile_id,
                VisualStyleMatchResultModel.importance_profile_id == importance_profile_id,
                VisualStyleMatchResultModel.carpet_style_profile_id == carpet_style_profile_id,
                VisualStyleMatchResultModel.match_version == match_version
            )
            .first()
        )

    @staticmethod
    def list_by_assessment(db: Session, assessment_id: uuid.UUID) -> List[VisualStyleMatchResultModel]:
        return (
            db.query(VisualStyleMatchResultModel)
            .options(joinedload(VisualStyleMatchResultModel.dimensions))
            .filter(VisualStyleMatchResultModel.assessment_id == assessment_id)
            .order_by(VisualStyleMatchResultModel.created_at.desc())
            .all()
        )

    @staticmethod
    def create(db: Session, match_model: VisualStyleMatchResultModel) -> VisualStyleMatchResultModel:
        db.add(match_model)
        db.commit()
        db.refresh(match_model)
        return match_model
