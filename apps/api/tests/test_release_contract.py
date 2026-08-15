"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Automated Release Contract & Verification Test Suite for v1.0.0-rc.1.
"""
import pytest
from app.core.config import (
    PRODUCTION_READINESS_VERSION,
    RELEASE_OPERATIONS_VERSION,
)
from app.domain.validation.constants import (
    RELEASE_CONTRACT_VERSION,
    VALIDATION_BENCHMARK_VERSION,
)
from app.domain.contracts import CANONICAL_STYLE_DNA


def test_release_versions_contract():
    assert RELEASE_CONTRACT_VERSION == "release-contract-v1"
    assert VALIDATION_BENCHMARK_VERSION == "validation-benchmark-v1"
    assert PRODUCTION_READINESS_VERSION == "production-readiness-v1"
    assert RELEASE_OPERATIONS_VERSION == "release-operations-v1"


def test_visual_style_match_canonical_labels():
    from app.db.models.preference_assessment import StyleMatchLabelEnum
    # Ensure WEAK is not in canonical labels
    labels = [e.value for e in StyleMatchLabelEnum]
    assert "VERY_STRONG" in labels
    assert "STRONG" in labels
    assert "MODERATE" in labels
    assert "LIMITED" in labels
    assert "LOW" in labels
    assert "WEAK" not in labels


def test_narrative_affinity_canonical_labels():
    from app.db.models.carpet_narrative_affinity import NarrativeAffinityLevelEnum
    labels = [e.value for e in NarrativeAffinityLevelEnum]
    assert "VERY_STRONG" in labels
    assert "STRONG" in labels
    assert "MODERATE" in labels
    assert "LIMITED" in labels


def test_historical_connection_canonical_labels():
    from app.db.models.carpet_historical_connection import HistoricalConnectionLevelEnum
    labels = [e.value for e in HistoricalConnectionLevelEnum]
    assert "VERY_CLOSE" in labels
    assert "CLOSE" in labels
    assert "MODERATE" in labels
    assert "LIMITED" in labels


def test_style_dna_9d_dimensions():
    keys = [d["key"] for d in CANONICAL_STYLE_DNA]
    expected_9d = [
        "color_energy",
        "color_diversity",
        "contrast",
        "warmth",
        "visual_complexity",
        "structural_order",
        "rhythm_repetition",
        "focal_strength",
        "form_language"
    ]
    assert keys == expected_9d
    assert len(keys) == 9
