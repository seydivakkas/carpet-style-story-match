from typing import Dict, List, Any
from app.db.models.preference_assessment import TextChoiceEnum
from app.domain.contracts import CANONICAL_STYLE_DNA

TEXT_PREFERENCE_EVIDENCE_VERSION = "text-preference-evidence-v1"

TEXT_CHOICE_MAP: Dict[TextChoiceEnum, float] = {
    TextChoiceEnum.STRONGLY_A: -1.00,
    TextChoiceEnum.SLIGHTLY_A: -0.50,
    TextChoiceEnum.NEUTRAL: 0.00,
    TextChoiceEnum.SLIGHTLY_B: +0.50,
    TextChoiceEnum.STRONGLY_B: +1.00,
}

CANONICAL_TEXT_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question_key": "T1_ROOM_ROLE",
        "order": 1,
        "prompt_tr": "Bir halının odadaki rolü sana hangisiyle daha yakın geliyor?",
        "option_a_tr": "Ortama sakin biçimde uyum sağlaması.",
        "option_b_tr": "Mekânda daha canlı ve dikkat çekici bir etki oluşturması.",
        "primary_dimension": "color_energy",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    },
    {
        "question_key": "T2_COLOR_DIVERSITY",
        "order": 2,
        "prompt_tr": "Bir halıda renk kullanımı açısından hangisini daha çok tercih edersin?",
        "option_a_tr": "Az sayıda ve kontrollü renk.",
        "option_b_tr": "Daha zengin ve çeşitli renk paleti.",
        "primary_dimension": "color_diversity",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    },
    {
        "question_key": "T3_CONTRAST",
        "order": 3,
        "prompt_tr": "Desen ve renk geçişlerinde hangisi sana daha yakın?",
        "option_a_tr": "Daha yumuşak ve birbirine yaklaşan geçişler.",
        "option_b_tr": "Daha belirgin ve güçlü ayrımlar.",
        "primary_dimension": "contrast",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    },
    {
        "question_key": "T4_WARMTH",
        "order": 4,
        "prompt_tr": "Renk atmosferinde hangisini daha çok tercih edersin?",
        "option_a_tr": "Mavi, turkuaz ve serin tonların öne çıktığı bir atmosfer.",
        "option_b_tr": "Kırmızı, turuncu, sarı ve sıcak tonların öne çıktığı bir atmosfer.",
        "primary_dimension": "warmth",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    },
    {
        "question_key": "T5_STRUCTURAL_ORDER",
        "order": 5,
        "prompt_tr": "Kompozisyon düzeninde hangisi sana daha yakın?",
        "option_a_tr": "Daha serbest, asimetrik ve beklenmedik yerleşimler.",
        "option_b_tr": "Daha dengeli, düzenli ve simetrik yerleşimler.",
        "primary_dimension": "structural_order",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    },
    {
        "question_key": "T6_FORM_LANGUAGE",
        "order": 6,
        "prompt_tr": "Desenlerin biçim dili açısından hangisini daha çok tercih edersin?",
        "option_a_tr": "Köşeli, doğrusal ve geometrik formlar.",
        "option_b_tr": "Kıvrımlı, akışkan ve organik formlar.",
        "primary_dimension": "form_language",
        "response_scale": ["STRONGLY_A", "SLIGHTLY_A", "NEUTRAL", "SLIGHTLY_B", "STRONGLY_B"]
    }
]

# 6 Questions x 9 Dimensions Canonical Evidence Weights Matrix
# Order of columns: [color_energy, color_diversity, contrast, warmth, visual_complexity, structural_order, rhythm_repetition, focal_strength, form_language]
EVIDENCE_MATRIX_WEIGHTS: Dict[str, List[float]] = {
    "T1_ROOM_ROLE":        [1.00, 0.00, 0.20, 0.00, 0.00, 0.00, 0.00, 0.25, 0.00],
    "T2_COLOR_DIVERSITY": [0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    "T3_CONTRAST":        [0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    "T4_WARMTH":          [0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    "T5_STRUCTURAL_ORDER":[0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00],
    "T6_FORM_LANGUAGE":    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00],
}
