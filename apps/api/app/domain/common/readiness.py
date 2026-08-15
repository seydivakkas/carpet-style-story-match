"""Shared Style DNA readiness derivation helper."""
import enum
from typing import Optional, Any


class StyleDnaReadinessEnum(str, enum.Enum):
    """Shared enum for Style DNA analysis readiness states."""
    NO_PRIMARY_IMAGE = "NO_PRIMARY_IMAGE"
    STYLE_DNA_MISSING = "STYLE_DNA_MISSING"
    STYLE_DNA_FAILED = "STYLE_DNA_FAILED"
    STYLE_DNA_PARTIAL = "STYLE_DNA_PARTIAL"
    STYLE_DNA_COMPLETE = "STYLE_DNA_COMPLETE"


def derive_style_dna_readiness(
    primary_image: Optional[Any],
    current_profile: Optional[Any]
) -> StyleDnaReadinessEnum:
    """Derives Style DNA readiness state from primary image and current profile."""
    if not primary_image:
        return StyleDnaReadinessEnum.NO_PRIMARY_IMAGE
    elif not current_profile:
        return StyleDnaReadinessEnum.STYLE_DNA_MISSING
    elif current_profile.status.value == "FAILED":
        return StyleDnaReadinessEnum.STYLE_DNA_FAILED
    elif current_profile.status.value == "PARTIAL":
        return StyleDnaReadinessEnum.STYLE_DNA_PARTIAL
    elif current_profile.status.value == "COMPLETE":
        return StyleDnaReadinessEnum.STYLE_DNA_COMPLETE
    else:
        return StyleDnaReadinessEnum.STYLE_DNA_MISSING
