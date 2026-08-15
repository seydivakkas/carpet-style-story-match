import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class AssessmentStatus(str, enum.Enum):
    TEXT_PENDING = "TEXT_PENDING"
    TEXT_COMPLETE = "TEXT_COMPLETE"
    VISUAL_PENDING = "VISUAL_PENDING"
    VISUAL_COMPLETE = "VISUAL_COMPLETE"
    PROFILE_READY = "PROFILE_READY"
    PROFILE_REVIEWED = "PROFILE_REVIEWED"

class PreferenceDimensionStatus(str, enum.Enum):
    MEASURED = "MEASURED"
    NOT_MEASURED = "NOT_MEASURED"

class UserProfileStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"

class UserPreferenceProvenanceEnum(str, enum.Enum):
    INFERRED = "INFERRED"
    USER_CONFIRMED = "USER_CONFIRMED"
    USER_OVERRIDDEN = "USER_OVERRIDDEN"

class ConfidenceStatusEnum(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    NO_EVIDENCE = "NO_EVIDENCE"

class TextChoiceEnum(str, enum.Enum):
    STRONGLY_A = "STRONGLY_A"
    SLIGHTLY_A = "SLIGHTLY_A"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_B = "SLIGHTLY_B"
    STRONGLY_B = "STRONGLY_B"

class VisualChoiceEnum(str, enum.Enum):
    STRONGLY_LEFT = "STRONGLY_LEFT"
    SLIGHTLY_LEFT = "SLIGHTLY_LEFT"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_RIGHT = "SLIGHTLY_RIGHT"
    STRONGLY_RIGHT = "STRONGLY_RIGHT"

class PreferenceAssessmentModel(Base):
    __tablename__ = "preference_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        SQLEnum(AssessmentStatus, name="assessment_status_enum", native_enum=False),
        nullable=False,
        default=AssessmentStatus.TEXT_PENDING
    )
    evidence_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text-preference-evidence-v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    responses: Mapped[List["TextPreferenceResponseModel"]] = relationship(
        "TextPreferenceResponseModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="TextPreferenceResponseModel.question_key"
    )
    profile: Mapped[Optional["TextPreferenceProfileModel"]] = relationship(
        "TextPreferenceProfileModel",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan"
    )
    visual_presentations: Mapped[List["VisualPreferencePresentationModel"]] = relationship(
        "VisualPreferencePresentationModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="VisualPreferencePresentationModel.stimulus_key"
    )
    visual_responses: Mapped[List["VisualPreferenceResponseModel"]] = relationship(
        "VisualPreferenceResponseModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="VisualPreferenceResponseModel.stimulus_key"
    )
    visual_profile: Mapped[Optional["VisualPreferenceProfileModel"]] = relationship(
        "VisualPreferenceProfileModel",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan"
    )
    user_preference_profile: Mapped[Optional["UserPreferenceProfileModel"]] = relationship(
        "UserPreferenceProfileModel",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan"
    )
    confidence_profile: Mapped[Optional["PreferenceConfidenceProfileModel"]] = relationship(
        "PreferenceConfidenceProfileModel",
        back_populates="assessment",
        uselist=False,
        cascade="all, delete-orphan"
    )

class TextPreferenceResponseModel(Base):
    __tablename__ = "text_preference_responses"

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
    question_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    choice: Mapped[TextChoiceEnum] = mapped_column(
        SQLEnum(TextChoiceEnum, name="text_choice_enum", native_enum=False),
        nullable=False
    )
    response_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="responses"
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "question_key", name="uq_assessment_question_key"),
    )

class TextPreferenceProfileModel(Base):
    __tablename__ = "text_preference_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    evidence_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text-preference-evidence-v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="profile"
    )
    dimensions: Mapped[List["TextPreferenceDimensionModel"]] = relationship(
        "TextPreferenceDimensionModel",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TextPreferenceDimensionModel.dimension_key"
    )

class TextPreferenceDimensionModel(Base):
    __tablename__ = "text_preference_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("text_preference_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dimension_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    status: Mapped[PreferenceDimensionStatus] = mapped_column(
        SQLEnum(PreferenceDimensionStatus, name="preference_dimension_status_enum", native_enum=False),
        nullable=False,
        default=PreferenceDimensionStatus.MEASURED
    )
    evidence_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    @property
    def key(self) -> str:
        return self.dimension_key

    profile: Mapped["TextPreferenceProfileModel"] = relationship(
        "TextPreferenceProfileModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "dimension_key", name="uq_text_profile_dimension_key"),
    )

# ---------------------------------------------------------
# VISUAL PREFERENCE MODELS (GÖREV 05)
# ---------------------------------------------------------

class VisualPreferencePresentationModel(Base):
    __tablename__ = "visual_preference_presentations"

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
    stimulus_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    stimulus_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="visual-preference-stimuli-v1"
    )
    left_variant: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    right_variant: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    left_asset_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    right_asset_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="visual_presentations"
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "stimulus_key", name="uq_assessment_stimulus_presentation"),
    )

class VisualPreferenceResponseModel(Base):
    __tablename__ = "visual_preference_responses"

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
    stimulus_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    choice: Mapped[VisualChoiceEnum] = mapped_column(
        SQLEnum(VisualChoiceEnum, name="visual_choice_enum", native_enum=False),
        nullable=False
    )
    canonical_direction: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="visual_responses"
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "stimulus_key", name="uq_assessment_stimulus_response"),
    )

class VisualPreferenceProfileModel(Base):
    __tablename__ = "visual_preference_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    evidence_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="visual-preference-evidence-v1"
    )
    stimulus_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="visual-preference-stimuli-v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="visual_profile"
    )
    dimensions: Mapped[List["VisualPreferenceDimensionModel"]] = relationship(
        "VisualPreferenceDimensionModel",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="VisualPreferenceDimensionModel.dimension_key"
    )

class VisualPreferenceDimensionModel(Base):
    __tablename__ = "visual_preference_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("visual_preference_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dimension_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    status: Mapped[PreferenceDimensionStatus] = mapped_column(
        SQLEnum(PreferenceDimensionStatus, name="preference_dimension_status_enum", native_enum=False),
        nullable=False,
        default=PreferenceDimensionStatus.MEASURED
    )
    evidence_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    @property
    def key(self) -> str:
        return self.dimension_key

    profile: Mapped["VisualPreferenceProfileModel"] = relationship(
        "VisualPreferenceProfileModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "dimension_key", name="uq_visual_profile_dimension_key"),
    )

# ---------------------------------------------------------
# MULTIMODAL USER PREFERENCE PROFILES (GÖREV 06)
# ---------------------------------------------------------

class UserPreferenceProfileModel(Base):
    __tablename__ = "user_preference_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    profile_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="multimodal-preference-v1"
    )
    status: Mapped[UserProfileStatusEnum] = mapped_column(
        SQLEnum(UserProfileStatusEnum, name="user_profile_status_enum", native_enum=False),
        nullable=False,
        default=UserProfileStatusEnum.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="user_preference_profile"
    )
    dimensions: Mapped[List["UserPreferenceDimensionModel"]] = relationship(
        "UserPreferenceDimensionModel",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="UserPreferenceDimensionModel.dimension_key"
    )
    confidence_profile: Mapped[Optional["PreferenceConfidenceProfileModel"]] = relationship(
        "PreferenceConfidenceProfileModel",
        back_populates="preference_profile",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "profile_version", name="uq_user_profile_assessment_version"),
    )

class UserPreferenceDimensionModel(Base):
    __tablename__ = "user_preference_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_preference_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dimension_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    inferred_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    final_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    status: Mapped[PreferenceDimensionStatus] = mapped_column(
        SQLEnum(PreferenceDimensionStatus, name="preference_dimension_status_enum", native_enum=False),
        nullable=False,
        default=PreferenceDimensionStatus.MEASURED
    )
    provenance: Mapped[UserPreferenceProvenanceEnum] = mapped_column(
        SQLEnum(UserPreferenceProvenanceEnum, name="user_preference_provenance_enum", native_enum=False),
        nullable=False,
        default=UserPreferenceProvenanceEnum.INFERRED
    )
    text_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    text_evidence_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    visual_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    visual_evidence_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def key(self) -> str:
        return self.dimension_key

    profile: Mapped["UserPreferenceProfileModel"] = relationship(
        "UserPreferenceProfileModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "dimension_key", name="uq_user_profile_dimension_key"),
    )

class PreferenceConfidenceProfileModel(Base):
    __tablename__ = "preference_confidence_profiles"

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
    preference_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_preference_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    confidence_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="preference-confidence-v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["PreferenceAssessmentModel"] = relationship(
        "PreferenceAssessmentModel",
        back_populates="confidence_profile"
    )
    preference_profile: Mapped["UserPreferenceProfileModel"] = relationship(
        "UserPreferenceProfileModel",
        back_populates="confidence_profile"
    )
    dimensions: Mapped[List["PreferenceConfidenceDimensionModel"]] = relationship(
        "PreferenceConfidenceDimensionModel",
        back_populates="confidence_profile",
        cascade="all, delete-orphan",
        order_by="PreferenceConfidenceDimensionModel.dimension_key"
    )

class PreferenceConfidenceDimensionModel(Base):
    __tablename__ = "preference_confidence_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    confidence_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preference_confidence_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dimension_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    status: Mapped[ConfidenceStatusEnum] = mapped_column(
        SQLEnum(ConfidenceStatusEnum, name="confidence_status_enum", native_enum=False),
        nullable=False,
        default=ConfidenceStatusEnum.AVAILABLE
    )
    modality_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    agreement: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    source_coverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    evidence_json: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    @property
    def key(self) -> str:
        return self.dimension_key

    confidence_profile: Mapped["PreferenceConfidenceProfileModel"] = relationship(
        "PreferenceConfidenceProfileModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("confidence_profile_id", "dimension_key", name="uq_confidence_profile_dimension_key"),
    )
