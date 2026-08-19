"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

UploadAnalysisModel database model for storing persistent 5-card analysis runs.
"""
import uuid
from datetime import datetime, timezone
import enum
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class UploadAnalysisStatusEnum(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED_BY_QUALITY = "BLOCKED_BY_QUALITY"


class UploadAnalysisModel(Base):
    __tablename__ = "upload_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    original_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )
    prepared_sha256: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True
    )
    image_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )
    mime_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="image/jpeg"
    )
    quality_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PASS"
    )
    status: Mapped[UploadAnalysisStatusEnum] = mapped_column(
        SQLEnum(UploadAnalysisStatusEnum, name="upload_analysis_status_enum"),
        nullable=False,
        default=UploadAnalysisStatusEnum.PROCESSING,
        index=True
    )

    # Structured extraction outputs
    style_dna_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    color_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    vlm_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    unified_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
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
