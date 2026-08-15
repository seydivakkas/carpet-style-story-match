import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class StyleProfileStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class StyleDimensionStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    FAILED = "FAILED"

class CarpetStyleProfileModel(Base):
    __tablename__ = "carpet_style_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    carpet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    algorithm_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="style-dna-v1.0.0"
    )
    analysis_input_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    analysis_scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="FULL_IMAGE"
    )
    status: Mapped[StyleProfileStatus] = mapped_column(
        SQLEnum(StyleProfileStatus, name="style_profile_status_enum"),
        nullable=False,
        default=StyleProfileStatus.COMPLETE
    )
    analyzed_width_px: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    analyzed_height_px: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    dimensions: Mapped[List["CarpetStyleDimensionModel"]] = relationship(
        "CarpetStyleDimensionModel",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="CarpetStyleDimensionModel.dimension_key"
    )

    __table_args__ = (
        UniqueConstraint("image_id", "algorithm_version", name="uq_profile_image_algorithm"),
    )

class CarpetStyleDimensionModel(Base):
    __tablename__ = "carpet_style_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_style_profiles.id", ondelete="CASCADE"),
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
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0
    )
    status: Mapped[StyleDimensionStatus] = mapped_column(
        SQLEnum(StyleDimensionStatus, name="style_dimension_status_enum"),
        nullable=False,
        default=StyleDimensionStatus.AVAILABLE
    )
    evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    method_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1"
    )

    @property
    def key(self) -> str:
        return self.dimension_key

    profile: Mapped["CarpetStyleProfileModel"] = relationship(
        "CarpetStyleProfileModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "dimension_key", name="uq_profile_dimension_key"),
    )
