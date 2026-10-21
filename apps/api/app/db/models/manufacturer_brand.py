"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

ManufacturerBrand model — Verified brand registry for multi-brand catalog architecture.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.carpet import CarpetModel

class ManufacturerBrandModel(Base):
    __tablename__ = "manufacturer_brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    brand_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Canonical lowercase key e.g. 'merinos', 'istikbal'"
    )
    brand_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable brand display name"
    )
    brand_website: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Official brand website URL"
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Brand logo image URL"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this brand source has been verified"
    )
    parser_module: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Python module path for brand-specific parser"
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

    # Relationship: one brand -> many carpets
    carpets: Mapped[List["CarpetModel"]] = relationship(
        "CarpetModel",
        back_populates="brand",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ManufacturerBrand key={self.brand_key!r} name={self.brand_name!r} verified={self.is_verified}>"
