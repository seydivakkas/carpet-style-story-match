"""
Visual Category Taxonomy Definitions (v1.0.0).

Frozen canonical categories for carpet composition analysis.
These describe pure geometric and structural layout from pixels.
They MUST NEVER include cultural or historical period labels.
"""
from enum import Enum
from typing import Dict, Any, List


class VisualCategoryKey(str, Enum):
    CENTRAL_MEDALLION = "central_medallion"
    ALL_OVER = "all_over"
    PRAYER_NICHE_LIKE = "prayer_niche_like"
    PANEL_LAYOUT = "panel_layout"
    LATTICE = "lattice"
    REPEATING_GEOMETRIC = "repeating_geometric"
    REPEATING_FLORAL = "repeating_floral"
    BORDER_DOMINANT = "border_dominant"
    MINIMAL_CONTEMPORARY = "minimal_contemporary"
    MIXED = "mixed"
    UNKNOWN = "unknown"


VISUAL_CATEGORY_TAXONOMY_VERSION = "visual-category-taxonomy-v1.0.0"

CANONICAL_VISUAL_CATEGORIES: List[Dict[str, Any]] = [
    {
        "category_key": VisualCategoryKey.CENTRAL_MEDALLION.value,
        "label_tr": "Merkezi Madalyonlu",
        "label_en": "Central Medallion",
        "description_en": "Dominant central focal medallion structure with field borders",
        "safety_note": "Describes visual focus location only"
    },
    {
        "category_key": VisualCategoryKey.ALL_OVER.value,
        "label_tr": "Tüm Yüzeye Dağılan",
        "label_en": "All-Over Pattern",
        "description_en": "Continuous repeating field pattern without a single central dominant medallion",
        "safety_note": "Describes spatial pattern distribution"
    },
    {
        "category_key": VisualCategoryKey.PRAYER_NICHE_LIKE.value,
        "label_tr": "Mihrap/Niş Benzeri Kompozisyon",
        "label_en": "Niche-Like Composition",
        "description_en": "Directional arch or niche-like structural outline",
        "safety_note": "CRITICAL: Purely visual geometry! Must NEVER imply 'prayer rug', 'namaz halısı', or religious function."
    },
    {
        "category_key": VisualCategoryKey.PANEL_LAYOUT.value,
        "label_tr": "Panelli Kompozisyon",
        "label_en": "Panel / Compartment Layout",
        "description_en": "Field partitioned into rectangular or polygonal grid compartments",
        "safety_note": "Describes layout partitioning"
    },
    {
        "category_key": VisualCategoryKey.LATTICE.value,
        "label_tr": "Kafes / Izgara Düzeni",
        "label_en": "Lattice / Trellis Layout",
        "description_en": "Interlocking diamond or geometric lattice structure across the field",
        "safety_note": "Describes geometric grid network"
    },
    {
        "category_key": VisualCategoryKey.REPEATING_GEOMETRIC.value,
        "label_tr": "Tekrarlı Geometrik",
        "label_en": "Repeating Geometric",
        "description_en": "Field dominated by repeated angular, polygonal, or linear geometric forms",
        "safety_note": "Geometric != Seljuk or Tribal"
    },
    {
        "category_key": VisualCategoryKey.REPEATING_FLORAL.value,
        "label_tr": "Tekrarlı Bitkisel",
        "label_en": "Repeating Botanical / Floral",
        "description_en": "Field dominated by repeated curvilinear, palmette, blossom, or vine motifs",
        "safety_note": "Floral != Safavid or Ottoman"
    },
    {
        "category_key": VisualCategoryKey.BORDER_DOMINANT.value,
        "label_tr": "Bordür Ağırlıklı",
        "label_en": "Border Dominant",
        "description_en": "Outer framing borders occupy a major visual proportion relative to the central field",
        "safety_note": "Describes visual area distribution"
    },
    {
        "category_key": VisualCategoryKey.MINIMAL_CONTEMPORARY.value,
        "label_tr": "Minimal / Çağdaş",
        "label_en": "Minimal / Contemporary",
        "description_en": "Sparse, low-complexity, monochrome, or broad tonal field composition",
        "safety_note": "Describes visual density"
    },
    {
        "category_key": VisualCategoryKey.MIXED.value,
        "label_tr": "Karma",
        "label_en": "Mixed / Hybrid",
        "description_en": "Combination of distinct compositional structures without a single dominant category",
        "safety_note": "Describes hybrid layout"
    },
    {
        "category_key": VisualCategoryKey.UNKNOWN.value,
        "label_tr": "Güvenle Sınıflandırılamadı",
        "label_en": "Unclassified / Unknown",
        "description_en": "Composition cannot be confidently assigned due to crop, occlusion, or ambiguity",
        "safety_note": "Unknown remains unknown"
    }
]
