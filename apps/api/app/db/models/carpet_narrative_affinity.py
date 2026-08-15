"""Database models for Explainable Narrative Affinity Engine v1."""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.db.models.carpet import CarpetModel
from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    UserNarrativeProfileModel,
    NarrativeInterestLevelEnum
)


class NarrativeAffinityStatusEnum(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class NarrativeAffinityLevelEnum(str, enum.Enum):
    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"


class NarrativeNotAvailableReasonEnum(str, enum.Enum):
    USER_NARRATIVE_SKIPPED = "USER_NARRATIVE_SKIPPED"
    NO_SELECTED_USER_THEMES = "NO_SELECTED_USER_THEMES"
    NO_CARPET_NARRATIVE_THEME_EVIDENCE = "NO_CARPET_NARRATIVE_THEME_EVIDENCE"
    ONLY_CONTESTED_CARPET_EVIDENCE = "ONLY_CONTESTED_CARPET_EVIDENCE"


class ThemeSupportStatusEnum(str, enum.Enum):
    DOCUMENTED = "DOCUMENTED"
    CONTEXTUAL = "CONTEXTUAL"
    CONTESTED_ONLY = "CONTESTED_ONLY"
    NO_EVIDENCE = "NO_EVIDENCE"


class NarrativeAffinityResultModel(Base):
    __tablename__ = "narrative_affinity_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_narrative_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_narrative_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    carpet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    affinity_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    carpet_narrative_snapshot_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    status: Mapped[NarrativeAffinityStatusEnum] = mapped_column(
        SQLEnum(NarrativeAffinityStatusEnum, name="narrative_affinity_status_enum", native_enum=False),
        nullable=False
    )
    not_available_reason: Mapped[Optional[NarrativeNotAvailableReasonEnum]] = mapped_column(
        SQLEnum(NarrativeNotAvailableReasonEnum, name="narrative_not_available_reason_enum", native_enum=False),
        nullable=True
    )
    affinity_level: Mapped[Optional[NarrativeAffinityLevelEnum]] = mapped_column(
        SQLEnum(NarrativeAffinityLevelEnum, name="narrative_affinity_level_enum", native_enum=False),
        nullable=True
    )
    confirmed_interest_coverage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    selected_theme_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    selected_interest_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    confirmed_matched_theme_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    confirmed_matched_interest_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    contested_overlap_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped[PreferenceAssessmentModel] = relationship("PreferenceAssessmentModel")
    user_narrative_profile: Mapped[UserNarrativeProfileModel] = relationship("UserNarrativeProfileModel")
    carpet: Mapped[CarpetModel] = relationship("CarpetModel")

    theme_results: Mapped[List["NarrativeAffinityThemeResultModel"]] = relationship(
        "NarrativeAffinityThemeResultModel",
        back_populates="affinity_result",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_narrative_profile_id",
            "carpet_id",
            "carpet_narrative_snapshot_hash",
            "affinity_version",
            name="uq_narrative_affinity_snapshot"
        ),
    )


class NarrativeAffinityThemeResultModel(Base):
    __tablename__ = "narrative_affinity_theme_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    affinity_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("narrative_affinity_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    theme_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    user_interest_level: Mapped[NarrativeInterestLevelEnum] = mapped_column(
        SQLEnum(NarrativeInterestLevelEnum, name="narrative_interest_level_enum", native_enum=False),
        nullable=False
    )
    user_interest_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    user_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )
    carpet_support_status: Mapped[ThemeSupportStatusEnum] = mapped_column(
        SQLEnum(ThemeSupportStatusEnum, name="theme_support_status_enum", native_enum=False),
        nullable=False
    )
    confirmed_match: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )
    contested_overlap: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )
    has_contested_evidence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    affinity_result: Mapped[NarrativeAffinityResultModel] = relationship(
        "NarrativeAffinityResultModel",
        back_populates="theme_results"
    )

    __table_args__ = (
        UniqueConstraint("affinity_result_id", "theme_key", name="uq_narrative_affinity_theme"),
    )
