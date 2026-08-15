import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class CarpetImageModel(Base):
    __tablename__ = "carpet_images"

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
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    storage_backend: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LOCAL_FILESYSTEM"
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True
    )
    byte_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    width_px: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    height_px: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    channels: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("carpet_id", "sha256", name="uq_carpet_image_sha256"),
        Index("ix_carpet_images_carpet_id_is_primary", "carpet_id", "is_primary"),
    )
