from typing import Dict, List, Any
from app.db.models.preference_assessment import TextChoiceEnum, VisualChoiceEnum

TEXT_PREFERENCE_EVIDENCE_VERSION = "text-preference-evidence-v1"
VISUAL_PREFERENCE_STIMULI_VERSION = "visual-preference-stimuli-v1"
VISUAL_PREFERENCE_EVIDENCE_VERSION = "visual-preference-evidence-v1"

MULTIMODAL_PREFERENCE_VERSION = "multimodal-preference-v1"
PREFERENCE_CONFIDENCE_VERSION = "preference-confidence-v1"

# 6 Text Questions definition
CANONICAL_TEXT_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question_key": "T1_ROOM_ROLE",
        "order": 1,
        "prompt_tr": "Halı odanın ana odak noktası mı olmalı, yoksa mekanı tamamlayan sakin bir zemin mi?",
        "option_a_tr": "Sakin zemin (düşük enerji)",
        "option_b_tr": "Odak noktası (canlı enerji)",
        "primary_dimension": "color_energy",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
    {
        "question_key": "T2_COLOR_DIVERSITY",
        "order": 2,
        "prompt_tr": "Nasıl bir renk paleti tercih edersiniz?",
        "option_a_tr": "Yalın ve ton-sür-ton palet",
        "option_b_tr": "Çok renkli ve zengin palet",
        "primary_dimension": "color_diversity",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
    {
        "question_key": "T3_CONTRAST",
        "order": 3,
        "prompt_tr": "Desen ve zemin arasındaki ayrım nasıl olmalı?",
        "option_a_tr": "Yumuşak geçişler ve düşük kontrast",
        "option_b_tr": "Keskin ayrışma ve yüksek kontrast",
        "primary_dimension": "contrast",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
    {
        "question_key": "T4_WARMTH",
        "order": 4,
        "prompt_tr": "Hangi renk tonu hissi alanınıza daha uygun?",
        "option_a_tr": "Soğuk tonlar (mavi, gri, ferah)",
        "option_b_tr": "Sıcak tonlar (kırmızı, sarı, toprak)",
        "primary_dimension": "warmth",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
    {
        "question_key": "T5_STRUCTURAL_ORDER",
        "order": 5,
        "prompt_tr": "Halı üzerindeki kompozisyon yapısı nasıl hissettirmeli?",
        "option_a_tr": "Serbest, doğal ve asimetrik",
        "option_b_tr": "Belirgin, dengeli ve simetrik",
        "primary_dimension": "structural_order",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
    {
        "question_key": "T6_FORM_LANGUAGE",
        "order": 6,
        "prompt_tr": "Motiflerin çizgi karakteri nasıl olmalı?",
        "option_a_tr": "Geometrik ve dik çizgiler",
        "option_b_tr": "Organik ve kavisli hatlar",
        "primary_dimension": "form_language",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"],
    },
]

# Canonical 9D Dimension Ordering
CANONICAL_DIMENSIONS_ORDER: List[str] = [
    "color_energy",        # D1
    "color_diversity",     # D2
    "contrast",           # D3
    "warmth",             # D4
    "visual_complexity",   # D5
    "structural_order",    # D6
    "rhythm_repetition",   # D7
    "focal_strength",      # D8
    "form_language",       # D9
]

# Canonical Text Choice Scale Mapping
TEXT_CHOICE_MAP: Dict[TextChoiceEnum, float] = {
    TextChoiceEnum.STRONGLY_A: -1.00,
    TextChoiceEnum.SLIGHTLY_A: -0.50,
    TextChoiceEnum.NEUTRAL:     0.00,
    TextChoiceEnum.SLIGHTLY_B: +0.50,
    TextChoiceEnum.STRONGLY_B: +1.00,
}

# Canonical Display Choice Scale Mapping for Visual Choices
VISUAL_CHOICE_DISPLAY_SCALE: Dict[VisualChoiceEnum, float] = {
    VisualChoiceEnum.STRONGLY_LEFT:  -1.00,
    VisualChoiceEnum.SLIGHTLY_LEFT:  -0.50,
    VisualChoiceEnum.NEUTRAL:         0.00,
    VisualChoiceEnum.SLIGHTLY_RIGHT: +0.50,
    VisualChoiceEnum.STRONGLY_RIGHT: +1.00,
}

# Frozen 6x9 Text Evidence Matrix
# Dimension order: [D1, D2, D3, D4, D5, D6, D7, D8, D9]
TEXT_EVIDENCE_MATRIX_WEIGHTS: Dict[str, List[float]] = {
    "T1_ROOM_ROLE":        [1.0, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.25, 0.0],
    "T2_COLOR_DIVERSITY": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  0.0],
    "T3_CONTRAST":        [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0,  0.0],
    "T4_WARMTH":          [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0,  0.0],
    "T5_STRUCTURAL_ORDER":[0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,  0.0], # D7 = 0.0 (strictly decoupled)
    "T6_FORM_LANGUAGE":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  1.0],
}
EVIDENCE_MATRIX_WEIGHTS = TEXT_EVIDENCE_MATRIX_WEIGHTS

# Frozen 6x9 Visual Evidence Matrix
# Dimension order: [D1, D2, D3, D4, D5, D6, D7, D8, D9]
VISUAL_EVIDENCE_MATRIX_WEIGHTS: Dict[str, List[float]] = {
    "V1_COLOR_ENERGY":     [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], # D1
    "V2_CONTRAST":         [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], # D3
    "V3_VISUAL_COMPLEXITY":[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0], # D5
    "V4_STRUCTURAL_ORDER": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0], # D6
    "V5_RHYTHM_REPETITION":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0], # D7
    "V6_FORM_LANGUAGE":    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], # D9
}

# Single Source of Truth for Visual Stimulus Calibration Thresholds
STIMULUS_TARGET_DELTA_MIN: float = 0.35
STIMULUS_MAX_NON_TARGET_DELTA: float = 0.15
