"""Constants for User Narrative Profile v1."""
from typing import Dict, List

USER_NARRATIVE_PROFILE_VERSION = "user-narrative-profile-v1"

MAX_PRIMARY_THEMES = 3
MAX_SECONDARY_THEMES = 3

# Frozen 8 Narrative Themes in canonical N1 -> N8 order
CANONICAL_NARRATIVE_THEMES: List[str] = [
    "nature_growth",
    "belonging_home",
    "journey_discovery",
    "continuity_connection",
    "balance_order",
    "renewal_transformation",
    "tradition_craft",
    "cultural_heritage",
]

NARRATIVE_THEME_LABELS: Dict[str, str] = {
    "nature_growth": "🌿 Doğa & Büyüme",
    "belonging_home": "🏠 Aidiyet & Yuva",
    "journey_discovery": "🧭 Yolculuk & Keşif",
    "continuity_connection": "🔗 Süreklilik & Bağ",
    "balance_order": "⚖️ Denge & Düzen",
    "renewal_transformation": "✨ Yenilenme & Dönüşüm",
    "tradition_craft": "🧵 Gelenek & Zanaat",
    "cultural_heritage": "🌍 Kültürel Miras",
}

# Interest Level Weights (Explicit User Interest Weights, NOT Importance Profile weights!)
INTEREST_LEVEL_WEIGHTS: Dict[str, float] = {
    "PRIMARY": 1.00,
    "SECONDARY": 0.60,
    "NOT_SELECTED": 0.00,
}
