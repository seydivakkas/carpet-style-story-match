"""Database models for Carpet Catalog + Curated Story Associations v1."""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.db.models.carpet import CarpetModel
from app.db.models.motif_knowledge import MotifModel, CuratedSourceModel, MotifStoryClaimModel


class MotifEvidenceTypeEnum(str, enum.Enum):
    CURATOR_CONFIRMED = "CURATOR_CONFIRMED"
    SOURCE_DOCUMENTED = "SOURCE_DOCUMENTED"
    UNCERTAIN = "UNCERTAIN"


class CarpetMotifAssociationModel(Base):
    __tablename__ = "carpet_motif_associations"

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
    motif_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motifs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    evidence_type: Mapped[MotifEvidenceTypeEnum] = mapped_column(
        SQLEnum(MotifEvidenceTypeEnum, name="motif_evidence_type_enum", native_enum=False),
        nullable=False,
        default=MotifEvidenceTypeEnum.CURATOR_CONFIRMED
    )
    curation_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )
    uncertainty_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
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

    carpet: Mapped[CarpetModel] = relationship(
        "CarpetModel",
        back_populates="motif_associations"
    )
    motif: Mapped[MotifModel] = relationship(
        "MotifModel"
    )
    presence_sources: Mapped[List["CarpetMotifAssociationSourceModel"]] = relationship(
        "CarpetMotifAssociationSourceModel",
        back_populates="association",
        cascade="all, delete-orphan"
    )
    story_associations: Mapped[List["CarpetStoryAssociationModel"]] = relationship(
        "CarpetStoryAssociationModel",
        back_populates="motif_association",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("carpet_id", "motif_id", name="uq_carpet_motif"),
    )


class CarpetMotifAssociationSourceModel(Base):
    __tablename__ = "carpet_motif_association_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    association_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_motif_associations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("curated_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    locator: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    source_note: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    association: Mapped["CarpetMotifAssociationModel"] = relationship(
        "CarpetMotifAssociationModel",
        back_populates="presence_sources"
    )
    source: Mapped[CuratedSourceModel] = relationship(
        "CuratedSourceModel"
    )

    __table_args__ = (
        UniqueConstraint("association_id", "source_id", name="uq_carpet_motif_source"),
    )


class CarpetStoryAssociationModel(Base):
    __tablename__ = "carpet_story_associations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    carpet_motif_association_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpet_motif_associations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motif_story_claims.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    applicability_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
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

    motif_association: Mapped["CarpetMotifAssociationModel"] = relationship(
        "CarpetMotifAssociationModel",
        back_populates="story_associations"
    )
    claim: Mapped[MotifStoryClaimModel] = relationship(
        "MotifStoryClaimModel"
    )

    __table_args__ = (
        UniqueConstraint("carpet_motif_association_id", "claim_id", name="uq_carpet_story_claim"),
    )
