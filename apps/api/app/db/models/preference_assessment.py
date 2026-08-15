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

class PreferenceDimensionStatus(str, enum.Enum):
    MEASURED = "MEASURED"
    NOT_MEASURED = "NOT_MEASURED"

class TextChoiceEnum(str, enum.Enum):
    STRONGLY_A = "STRONGLY_A"
    SLIGHTLY_A = "SLIGHTLY_A"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_B = "SLIGHTLY_B"
    STRONGLY_B = "STRONGLY_B"

class PreferenceAssessmentModel(Base):
    __tablename__ = "preference_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        SQLEnum(AssessmentStatus, name="assessment_status_enum"),
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
        SQLEnum(TextChoiceEnum, name="text_choice_enum"),
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
        SQLEnum(PreferenceDimensionStatus, name="preference_dimension_status_enum"),
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
