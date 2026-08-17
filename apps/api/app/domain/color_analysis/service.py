"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Color Analysis Service.
Coordinates image color extraction and produces validated ColorObservation lists.
"""
from typing import List
from app.domain.color_analysis.models import ColorObservation
from app.domain.color_analysis.extractor import ColorExtractor


class ColorAnalysisService:
    """Service providing deterministic visual color analysis for carpet images."""

    def __init__(self, extractor: ColorExtractor = None):
        self.extractor = extractor or ColorExtractor()

    def analyze_colors(self, raw_bytes: bytes, k: int = 5) -> List[ColorObservation]:
        """Extracts deterministic visual color observations from raw carpet image bytes."""
        return self.extractor.extract_colors(raw_bytes, k=k)
