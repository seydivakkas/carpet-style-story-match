"""
Motif Ontology Definitions (v1.0.0).

Controlled motif concepts and visual candidate mappings.
Separates visual candidate detection (PIXEL) from canonical/cultural verification.
Does NOT contain cultural stories, symbolism, or unverified claims.
"""
from enum import Enum
from typing import Dict, Any, List, Optional


MOTIF_ONTOLOGY_VERSION = "motif-ontology-v1.0.0"


class MotifFamily(str, Enum):
    GEOMETRIC = "GEOMETRIC"
    FLORAL_ORGANIC = "FLORAL_ORGANIC"
    COMPOSITIONAL = "COMPOSITIONAL"
    FIGURATIVE_LIKE = "FIGURATIVE_LIKE"
    UNRESOLVED = "UNRESOLVED"


class MotifType(str, Enum):
    DECORATIVE = "DECORATIVE"
    COMPOSITIONAL = "COMPOSITIONAL"
    STRUCTURAL = "STRUCTURAL"
    UNRESOLVED = "UNRESOLVED"


class DetectionMode(str, Enum):
    VISUAL_DIRECT = "VISUAL_DIRECT"
    REVIEW_REQUIRED_SEMANTIC = "REVIEW_REQUIRED_SEMANTIC"


class VisualCandidateKey(str, Enum):
    MEDALLION_LIKE = "medallion_like"
    NICHE_LIKE = "niche_like"
    STAR_LIKE = "star_like"
    ROSETTE_LIKE = "rosette_like"
    PALMETTE_LIKE = "palmette_like"
    LOTUS_LIKE = "lotus_like"
    VINE_SCROLL_LIKE = "vine_scroll_like"
    CLOUD_BAND_LIKE = "cloud_band_like"
    TREE_LIKE = "tree_like"
    HORN_LIKE = "horn_like"
    HUMAN_FIGURE_LIKE_GEOMETRIC = "human_figure_like_geometric"
    COMB_LIKE = "comb_like"
    HOOK_LIKE = "hook_like"
    LATTICE_LIKE = "lattice_like"
    LOZENGE_LIKE = "lozenge_like"
    OCTAGONAL_FORM = "octagonal_form"
    UNMAPPED_VISUAL_MOTIF = "unmapped_visual_motif"


# 13 Existing Production Canonical Motifs
CANONICAL_PRODUCTION_MOTIFS: List[str] = [
    "medallion",
    "mihrab",
    "palmette",
    "lotus",
    "rosette",
    "cloud-band",
    "scrolling-vine",
    "geometric-star",
    "ram-horn",
    "tree-of-life",
    "elibelinde",
    "comb",
    "mystery-hook"
]


MOTIF_ONTOLOGY_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "canonical_key": "medallion",
        "display_name_tr": "Madalyon",
        "display_name_en": "Medallion",
        "family": MotifFamily.COMPOSITIONAL.value,
        "motif_type": MotifType.COMPOSITIONAL.value,
        "visual_candidate_keys": [VisualCandidateKey.MEDALLION_LIKE.value, VisualCandidateKey.OCTAGONAL_FORM.value],
        "visual_definition": "Central radial, circular, oval, or polylobed geometric motif structure",
        "observable_features": ["radial symmetry", "central placement", "nested borders"],
        "ambiguous_with": ["geometric-star", "rosette"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "mihrab",
        "display_name_tr": "Mihrap / Niş",
        "display_name_en": "Niche / Mihrab Form",
        "family": MotifFamily.COMPOSITIONAL.value,
        "motif_type": MotifType.STRUCTURAL.value,
        "visual_candidate_keys": [VisualCandidateKey.NICHE_LIKE.value],
        "visual_definition": "Stepped or pointed arch outline at top of central field",
        "observable_features": ["directional apex", "vertical asymmetry", "arch contour"],
        "ambiguous_with": ["stepped-pediment", "gabled-panel"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "palmette",
        "display_name_tr": "Palmet",
        "display_name_en": "Palmette",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.PALMETTE_LIKE.value],
        "visual_definition": "Fan-like radiating leaf or floral motif structure",
        "observable_features": ["radiating petals", "curvilinear outline", "stem connection"],
        "ambiguous_with": ["lotus", "rosette"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "lotus",
        "display_name_tr": "Nilüfer / Lotus",
        "display_name_en": "Lotus Blossom",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.LOTUS_LIKE.value],
        "visual_definition": "Open cup-shaped floral blossom form",
        "observable_features": ["cup-shaped petals", "layered calyx", "symmetrical bloom"],
        "ambiguous_with": ["palmette", "rosette"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "rosette",
        "display_name_tr": "Rozet",
        "display_name_en": "Rosette",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.ROSETTE_LIKE.value],
        "visual_definition": "Circular stylized floral disc with surrounding petals",
        "observable_features": ["circular symmetry", "petal ring", "central core"],
        "ambiguous_with": ["geometric-star", "medallion"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "cloud-band",
        "display_name_tr": "Bulut Kümesi / Çin Bulutu",
        "display_name_en": "Cloud Band",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.CLOUD_BAND_LIKE.value],
        "visual_definition": "S-shaped or ribbon-like undulating cloud form",
        "observable_features": ["undulating ribbon", "curved scroll ends", "asymmetric flow"],
        "ambiguous_with": ["scrolling-vine", "mystery-hook"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "scrolling-vine",
        "display_name_tr": "Sarmaşık / Kıvrım Dal",
        "display_name_en": "Scrolling Vine / Islimi",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.VINE_SCROLL_LIKE.value],
        "visual_definition": "Continuous undulating or spiral stem connecting floral forms",
        "observable_features": ["continuous stem", "spiraling tendrils", "interleaved leaves"],
        "ambiguous_with": ["cloud-band", "lattice"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "geometric-star",
        "display_name_tr": "Geometrik Yıldız",
        "display_name_en": "Geometric Star",
        "family": MotifFamily.GEOMETRIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.STAR_LIKE.value, VisualCandidateKey.LOZENGE_LIKE.value],
        "visual_definition": "Multi-pointed polygonal star form (8-pointed, 6-pointed, or 12-pointed)",
        "observable_features": ["angular points", "radial point symmetry", "straight edge facets"],
        "ambiguous_with": ["rosette", "medallion"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "ram-horn",
        "display_name_tr": "Koçboynuzu",
        "display_name_en": "Horn Form / Ram's Horn",
        "family": MotifFamily.GEOMETRIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.HORN_LIKE.value, VisualCandidateKey.HOOK_LIKE.value],
        "visual_definition": "Symmetrical outward-curving spiral or hooked horn-like arms",
        "observable_features": ["paired spiral hooks", "bilateral symmetry", "angular or curved horns"],
        "ambiguous_with": ["mystery-hook", "elibelinde"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "tree-of-life",
        "display_name_tr": "Hayat Ağacı Biçimi",
        "display_name_en": "Tree-Like Form",
        "family": MotifFamily.FLORAL_ORGANIC.value,
        "motif_type": MotifType.STRUCTURAL.value,
        "visual_candidate_keys": [VisualCandidateKey.TREE_LIKE.value],
        "visual_definition": "Vertical trunk form with branching lateral motifs",
        "observable_features": ["central vertical axis", "ascending branches", "top apex"],
        "ambiguous_with": ["mihrab", "scrolling-vine"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "elibelinde",
        "display_name_tr": "Eli Belinde Biçimi",
        "display_name_en": "Geometric Humanoid Form / Hands on Hips",
        "family": MotifFamily.FIGURATIVE_LIKE.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.HUMAN_FIGURE_LIKE_GEOMETRIC.value],
        "visual_definition": "Stylized geometric figure with triangular body and lateral bent arm-like projections",
        "observable_features": ["triangular torso", "lateral arm angles", "head apex"],
        "ambiguous_with": ["ram-horn", "geometric-star"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "comb",
        "display_name_tr": "Tarak Biçimi",
        "display_name_en": "Comb-Like Form",
        "family": MotifFamily.GEOMETRIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.COMB_LIKE.value],
        "visual_definition": "Linear bar with parallel vertical tooth-like projections",
        "observable_features": ["parallel teeth", "linear base bar", "regular spacing"],
        "ambiguous_with": ["fringe-border", "crenellated-line"],
        "detection_mode": DetectionMode.VISUAL_DIRECT.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    },
    {
        "canonical_key": "mystery-hook",
        "display_name_tr": "Çengel / Çengelli Geometri",
        "display_name_en": "Hook Form / Latch-Hook",
        "family": MotifFamily.GEOMETRIC.value,
        "motif_type": MotifType.DECORATIVE.value,
        "visual_candidate_keys": [VisualCandidateKey.HOOK_LIKE.value, VisualCandidateKey.LOZENGE_LIKE.value],
        "visual_definition": "Angular hook projection extending from diamond or medallion perimeter",
        "observable_features": ["90-degree hook projection", "perimeter attachment", "repeating hook fringe"],
        "ambiguous_with": ["ram-horn", "comb"],
        "detection_mode": DetectionMode.REVIEW_REQUIRED_SEMANTIC.value,
        "active": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION
    }
]
