"""Database models for Curated Motif Story + Source Provenance v1."""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class SourceTypeEnum(str, enum.Enum):
    MUSEUM_OBJECT = "MUSEUM_OBJECT"
    MUSEUM_CATALOG = "MUSEUM_CATALOG"
    ACADEMIC_ARTICLE = "ACADEMIC_ARTICLE"
    ACADEMIC_BOOK = "ACADEMIC_BOOK"
    INSTITUTIONAL_PUBLICATION = "INSTITUTIONAL_PUBLICATION"
    ARCHIVE_RECORD = "ARCHIVE_RECORD"
    OTHER = "OTHER"


class MotifStoryStatusEnum(str, enum.Enum):
    DOCUMENTED = "DOCUMENTED"
    CONTEXTUAL = "CONTEXTUAL"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"


class CuratedSourceModel(Base):
    __tablename__ = "curated_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    source_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    source_type: Mapped[SourceTypeEnum] = mapped_column(
        SQLEnum(SourceTypeEnum, name="source_type_enum", native_enum=False),
        nullable=False,
        default=SourceTypeEnum.OTHER
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    citation_text: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )
    creator_or_institution: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    publication_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    isbn: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    rights_note: Mapped[Optional[str]] = mapped_column(
        String(500),
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

    claim_links: Mapped[List["MotifStoryClaimSourceModel"]] = relationship(
        "MotifStoryClaimSourceModel",
        back_populates="source"
    )


class MotifModel(Base):
    __tablename__ = "motifs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    motif_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    name_tr: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    name_en: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    visual_description_tr: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )
    visual_description_en: Mapped[Optional[str]] = mapped_column(
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

    story_claims: Mapped[List["MotifStoryClaimModel"]] = relationship(
        "MotifStoryClaimModel",
        back_populates="motif",
        cascade="all, delete-orphan"
    )


class MotifStoryClaimModel(Base):
    __tablename__ = "motif_story_claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    claim_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    motif_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motifs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    status: Mapped[MotifStoryStatusEnum] = mapped_column(
        SQLEnum(MotifStoryStatusEnum, name="motif_story_status_enum", native_enum=False),
        nullable=False,
        default=MotifStoryStatusEnum.DOCUMENTED
    )
    claim_text_tr: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True
    )
    claim_text_en: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True
    )
    context_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )
    contest_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )
    uncertainty_note: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )
    knowledge_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="motif-story-knowledge-v1"
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

    motif: Mapped["MotifModel"] = relationship(
        "MotifModel",
        back_populates="story_claims"
    )
    sources: Mapped[List["MotifStoryClaimSourceModel"]] = relationship(
        "MotifStoryClaimSourceModel",
        back_populates="claim",
        cascade="all, delete-orphan"
    )
    themes: Mapped[List["MotifStoryClaimThemeModel"]] = relationship(
        "MotifStoryClaimThemeModel",
        back_populates="claim",
        cascade="all, delete-orphan"
    )


class MotifStoryClaimSourceModel(Base):
    __tablename__ = "motif_story_claim_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motif_story_claims.id", ondelete="CASCADE"),
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

    claim: Mapped["MotifStoryClaimModel"] = relationship(
        "MotifStoryClaimModel",
        back_populates="sources"
    )
    source: Mapped["CuratedSourceModel"] = relationship(
        "CuratedSourceModel",
        back_populates="claim_links"
    )

    __table_args__ = (
        UniqueConstraint("claim_id", "source_id", name="uq_claim_source"),
    )


class MotifStoryClaimThemeModel(Base):
    __tablename__ = "motif_story_claim_themes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("motif_story_claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    theme_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    claim: Mapped["MotifStoryClaimModel"] = relationship(
        "MotifStoryClaimModel",
        back_populates="themes"
    )

    __table_args__ = (
        UniqueConstraint("claim_id", "theme_key", name="uq_claim_theme"),
    )
