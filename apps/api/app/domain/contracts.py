from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Frozen 9D Style DNA definitions in canonical order (D1 -> D9)
CANONICAL_STYLE_DNA: List[Dict[str, Any]] = [
    {
        "code": "D1",
        "key": "color_energy",
        "label_tr": "Renk Enerjisi",
        "min_label": "Sakin",
        "max_label": "Canlı"
    },
    {
        "code": "D2",
        "key": "color_diversity",
        "label_tr": "Renk Çeşitliliği",
        "min_label": "Sınırlı Palet",
        "max_label": "Zengin Palet"
    },
    {
        "code": "D3",
        "key": "contrast",
        "label_tr": "Kontrast",
        "min_label": "Yumuşak",
        "max_label": "Güçlü"
    },
    {
        "code": "D4",
        "key": "warmth",
        "label_tr": "Renk Sıcaklığı",
        "min_label": "Soğuk",
        "max_label": "Sıcak"
    },
    {
        "code": "D5",
        "key": "visual_complexity",
        "label_tr": "Görsel Karmaşıklık",
        "min_label": "Sade",
        "max_label": "Detaylı"
    },
    {
        "code": "D6",
        "key": "structural_order",
        "label_tr": "Düzen & Simetri",
        "min_label": "Serbest",
        "max_label": "Düzenli"
    },
    {
        "code": "D7",
        "key": "rhythm_repetition",
        "label_tr": "Ritim & Tekrar",
        "min_label": "Tekil",
        "max_label": "Ritmik/Tekrarlı"
    },
    {
        "code": "D8",
        "key": "focal_strength",
        "label_tr": "Odak Gücü",
        "min_label": "Dağıtılmış",
        "max_label": "Güçlü Odak"
    },
    {
        "code": "D9",
        "key": "form_language",
        "label_tr": "Form Dili",
        "min_label": "Geometrik",
        "max_label": "Organik"
    }
]

# Frozen 8 Narrative Themes definitions (N1 -> N8)
CANONICAL_NARRATIVE_THEMES: List[Dict[str, Any]] = [
    {
        "code": "N1",
        "key": "nature_growth",
        "icon": "🌿",
        "label_tr": "Doğa & Büyüme",
        "description": "Flora, botanical motifs, life cycle, and natural vitality"
    },
    {
        "code": "N2",
        "key": "belonging_home",
        "icon": "🏠",
        "label_tr": "Aidiyet & Yuva",
        "description": "Protection, sanctuary, tribal identity, and home hearth"
    },
    {
        "code": "N3",
        "key": "journey_discovery",
        "icon": "🧭",
        "label_tr": "Yolculuk & Keşif",
        "description": "Migration routes, nomadic paths, horizons, and spiritual quests"
    },
    {
        "code": "N4",
        "key": "continuity_connection",
        "icon": "🔗",
        "label_tr": "Süreklilik & Bağ",
        "description": "Interlocking patterns, lineage, family ties, and eternal loops"
    },
    {
        "code": "N5",
        "key": "balance_order",
        "icon": "⚖️",
        "label_tr": "Denge & Düzen",
        "description": "Harmonic symmetry, cosmic order, dualities, and proportion"
    },
    {
        "code": "N6",
        "key": "renewal_transformation",
        "icon": "✨",
        "label_tr": "Yenilenme & Dönüşüm",
        "description": "Seasonal shifts, rebirth, water flow, and protective talismans"
    },
    {
        "code": "N7",
        "key": "tradition_craft",
        "icon": "🧵",
        "label_tr": "Gelenek & Zanaat",
        "description": "Dye techniques, weaving mastery, loom heritage, and skill"
    },
    {
        "code": "N8",
        "key": "cultural_heritage",
        "icon": "🌍",
        "label_tr": "Kültürel Miras",
        "description": "Regional archetypes, historic iconography, and documented provenance"
    }
]

class StyleDimensionContract(BaseModel):
    code: str
    key: str
    label_tr: str
    min_label: str
    max_label: str

class StyleDNAContractResponse(BaseModel):
    total_dimensions: int = 9
    dimensions: List[StyleDimensionContract]

class NarrativeThemeContract(BaseModel):
    code: str
    key: str
    icon: str
    label_tr: str
    description: str

class NarrativeThemesContractResponse(BaseModel):
    total_themes: int = 8
    themes: List[NarrativeThemeContract]
