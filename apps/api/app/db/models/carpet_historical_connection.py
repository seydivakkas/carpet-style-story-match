"""Database models for Historical Connection Engine v1."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint,
    CheckConstraint,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.carpet import CarpetModel
    from app.db.models.carpet_style_profile import CarpetStyleProfileModel
    from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel

class HistoricalConnectionStatusEnum(str, Enum):
    """Result availability status for historical connection evaluation."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class HistoricalConnectionNotAvailableReasonEnum(str, Enum):
    """Reason code when historical connection cannot be evaluated."""
    INSUFFICIENT_COMPARABLE_DIMENSIONS = "INSUFFICIENT_COMPARABLE_DIMENSIONS"


class HistoricalConnectionLevelEnum(str, Enum):
    """Categorical visual similarity levels for historical connection."""
    VERY_CLOSE = "VERY_CLOSE"
    CLOSE = "CLOSE"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"


class HistoricalConnectionResultModel(Base):
    """Persisted result of a pairwise visual Style DNA comparison with a historical reference."""

    __tablename__ = "historical_connection_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    target_carpet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_style_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_style_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    historical_carpet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    historical_reference_metadata_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("historical_reference_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    historical_style_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_style_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    connection_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="historical-connection-v1"
    )

    status: Mapped[HistoricalConnectionStatusEnum] = mapped_column(
        SQLEnum(HistoricalConnectionStatusEnum, name="historical_connection_status_enum", native_enum=False),
        nullable=False
    )
    not_available_reason: Mapped[Optional[HistoricalConnectionNotAvailableReasonEnum]] = mapped_column(
        SQLEnum(HistoricalConnectionNotAvailableReasonEnum, name="historical_connection_not_available_reason_enum", native_enum=False),
        nullable=True
    )

    style_similarity: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    connection_level: Mapped[Optional[HistoricalConnectionLevelEnum]] = mapped_column(
        SQLEnum(HistoricalConnectionLevelEnum, name="historical_connection_level_enum", native_enum=False),
        nullable=True
    )

    comparable_dimension_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    dimension_coverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now()
    )

    target_carpet: Mapped["CarpetModel"] = relationship("CarpetModel", foreign_keys=[target_carpet_id])
    target_style_profile: Mapped["CarpetStyleProfileModel"] = relationship("CarpetStyleProfileModel", foreign_keys=[target_style_profile_id])

    historical_carpet: Mapped["CarpetModel"] = relationship("CarpetModel", foreign_keys=[historical_carpet_id])
    historical_reference_metadata: Mapped["HistoricalReferenceMetadataModel"] = relationship("HistoricalReferenceMetadataModel", foreign_keys=[historical_reference_metadata_id])
    historical_style_profile: Mapped["CarpetStyleProfileModel"] = relationship("CarpetStyleProfileModel", foreign_keys=[historical_style_profile_id])

    dimensions: Mapped[List["HistoricalConnectionDimensionModel"]] = relationship(
        "HistoricalConnectionDimensionModel",
        back_populates="historical_connection",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "target_style_profile_id",
            "historical_style_profile_id",
            "connection_version",
            name="uq_historical_connection_profiles"
        ),
        CheckConstraint(
            "style_similarity IS NULL OR (style_similarity >= 0.0 AND style_similarity <= 1.0)",
            name="check_hist_conn_similarity_range"
        ),
        CheckConstraint(
            "dimension_coverage >= 0.0 AND dimension_coverage <= 1.0",
            name="check_hist_conn_coverage_range"
        ),
    )


class HistoricalConnectionDimensionModel(Base):
    """Persisted snapshot of pairwise comparison for a single Style DNA dimension."""

    __tablename__ = "historical_connection_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    historical_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("historical_connection_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dimension_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    target_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    target_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    target_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    reference_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    reference_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    reference_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    difference: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    similarity: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    comparable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now()
    )

    historical_connection: Mapped["HistoricalConnectionResultModel"] = relationship(
        "HistoricalConnectionResultModel",
        back_populates="dimensions"
    )

    __table_args__ = (
        UniqueConstraint("historical_connection_id", "dimension_key", name="uq_historical_connection_dimension"),
        CheckConstraint("difference IS NULL OR (difference >= 0.0 AND difference <= 1.0)", name="check_hist_conn_dim_diff_range"),
        CheckConstraint("similarity IS NULL OR (similarity >= 0.0 AND similarity <= 1.0)", name="check_hist_conn_dim_sim_range"),
    )
