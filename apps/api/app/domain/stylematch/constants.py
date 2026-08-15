"""Domain constants for Visual Style Match Engine v1."""
from typing import Dict
from app.db.models.preference_assessment import StyleMatchLabelEnum

VISUAL_STYLE_MATCH_VERSION: str = "visual-style-match-v1"

MATCH_MIN_WEIGHTED_COVERAGE: float = 0.70
MATCH_MIN_COMPARABLE_DIMENSIONS: int = 6

MATCH_LABEL_TR: Dict[StyleMatchLabelEnum, str] = {
    StyleMatchLabelEnum.VERY_STRONG: "Çok Güçlü Stil Eşleşmesi",
    StyleMatchLabelEnum.STRONG: "Güçlü Stil Eşleşmesi",
    StyleMatchLabelEnum.MODERATE: "Orta Düzey Stil Eşleşmesi",
    StyleMatchLabelEnum.LIMITED: "Sınırlı Stil Eşleşmesi",
    StyleMatchLabelEnum.LOW: "Düşük Stil Eşleşmesi",
}

def get_match_label(score_100: float) -> StyleMatchLabelEnum:
    """Return canonical match label based on score_100."""
    if score_100 >= 90.0:
        return StyleMatchLabelEnum.VERY_STRONG
    elif score_100 >= 75.0:
        return StyleMatchLabelEnum.STRONG
    elif score_100 >= 60.0:
        return StyleMatchLabelEnum.MODERATE
    elif score_100 >= 45.0:
        return StyleMatchLabelEnum.LIMITED
    else:
        return StyleMatchLabelEnum.LOW
