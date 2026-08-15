"""Database models for Historical Reference Collection v1."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class HistoricalSourceRoleEnum(str, Enum):
    """Source roles for historical reference objects."""
    PRIMARY_OBJECT_RECORD = "PRIMARY_OBJECT_RECORD"
    SUPPORTING_REFERENCE = "SUPPORTING_REFERENCE"


class HistoricalReferenceMetadataModel(Base):
    """Source-reported historical metadata 1:1 linked to a CarpetModel(source_type=HISTORICAL)."""

    __tablename__ = "historical_reference_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    carpet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    reference_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )

    institution_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    object_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    accession_number: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    object_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    culture: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    period: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    dynasty_or_tradition: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    date_display: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    date_start_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    date_end_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    geography: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    medium: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    dimensions_text: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    credit_line: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    object_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    source_image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    rights_statement: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    open_access: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True
    )

    curation_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    schema_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="historical-reference-curation-v1"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now()
    )

    carpet: Mapped["CarpetModel"] = relationship("CarpetModel")
    source_links: Mapped[List["HistoricalReferenceSourceModel"]] = relationship(
        "HistoricalReferenceSourceModel",
        back_populates="historical_reference",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("institution_name", "object_identifier", name="uq_historical_ref_institution_object_id"),
    )


class HistoricalReferenceSourceModel(Base):
    """Link table mapping a historical reference record to a CuratedSourceModel."""

    __tablename__ = "historical_reference_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    historical_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("historical_reference_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("curated_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    source_role: Mapped[HistoricalSourceRoleEnum] = mapped_column(
        SQLEnum(HistoricalSourceRoleEnum, name="historical_source_role_enum", native_enum=False),
        nullable=False
    )
    locator: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    source_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now()
    )

    historical_reference: Mapped["HistoricalReferenceMetadataModel"] = relationship(
        "HistoricalReferenceMetadataModel",
        back_populates="source_links"
    )
    source: Mapped["CuratedSourceModel"] = relationship("CuratedSourceModel")

    __table_args__ = (
        UniqueConstraint("historical_reference_id", "source_id", name="uq_historical_ref_source"),
    )
