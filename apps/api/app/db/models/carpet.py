import uuid
from datetime import datetime, timezone
import enum
from typing import Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    CheckConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class CarpetSourceType(str, enum.Enum):
    CATALOG = "CATALOG"
    USER_UPLOAD = "USER_UPLOAD"
    HISTORICAL = "HISTORICAL"
    MANUAL = "MANUAL"

class CarpetModel(Base):
    __tablename__ = "carpets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    sku: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    collection: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    width_cm: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    height_cm: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    material: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    style_label: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    source_type: Mapped[CarpetSourceType] = mapped_column(
        SQLEnum(CarpetSourceType, name="carpet_source_type_enum"),
        nullable=False,
        default=CarpetSourceType.CATALOG
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
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

    motif_associations: Mapped[list["CarpetMotifAssociationModel"]] = relationship(
        "CarpetMotifAssociationModel",
        back_populates="carpet",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("width_cm IS NULL OR width_cm > 0", name="ck_carpets_width_positive"),
        CheckConstraint("height_cm IS NULL OR height_cm > 0", name="ck_carpets_height_positive"),
        CheckConstraint("length(trim(name)) > 0", name="ck_carpets_name_not_empty"),
    )
