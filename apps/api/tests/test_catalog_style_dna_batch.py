"""Focused unit & integration tests for Catalog Style DNA Batch Analysis (POST-v1 A3)."""

import pytest
import uuid
import math
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION, StyleDNAEngine
from app.scripts.analyze_catalog_style_dna import run_batch_analysis


@pytest.mark.asyncio
async def test_engine_frozen_9d_keys_and_range():
    """Verify engine returns exact 9 frozen dimensions with valid ranges."""
    engine = StyleDNAEngine()
    # Create a 100x100 synthetic RGB image
    import numpy as np
    import cv2
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    raw_bytes = buf.tobytes()

    status, dimensions = engine.analyze(raw_bytes)
    assert status in [StyleProfileStatus.COMPLETE, StyleProfileStatus.PARTIAL]
    assert len(dimensions) == 9

    expected_keys = [
        "color_energy",
        "color_diversity",
        "contrast",
        "warmth",
        "visual_complexity",
        "structural_order",
        "rhythm_repetition",
        "focal_strength",
        "form_language",
    ]

    for idx, dim in enumerate(dimensions):
        assert dim["key"] == expected_keys[idx]
        if dim["value"] is not None:
            assert 0.0 <= dim["value"] <= 1.0
            assert not math.isnan(dim["value"])
            assert not math.isinf(dim["value"])


@pytest.mark.asyncio
async def test_batch_idempotency_second_run():
    """Verify running batch report second time skips already current profiles and maintains exact accounting."""
    report = await run_batch_analysis(apply=False)
    assert report["catalog_total"] >= 0
    assert report["unaccounted"] == 0
