import pytest
from app.domain.contracts import CANONICAL_STYLE_DNA, CANONICAL_NARRATIVE_THEMES

@pytest.mark.asyncio
async def test_style_dna_contract_endpoint(client):
    response = await client.get("/api/v1/meta/style-dna")
    assert response.status_code == 200
    data = response.json()
    assert data["total_dimensions"] == 9
    dims = data["dimensions"]
    assert len(dims) == 9

    expected_keys = [
        ("D1", "color_energy"),
        ("D2", "color_diversity"),
        ("D3", "contrast"),
        ("D4", "warmth"),
        ("D5", "visual_complexity"),
        ("D6", "structural_order"),
        ("D7", "rhythm_repetition"),
        ("D8", "focal_strength"),
        ("D9", "form_language"),
    ]

    for idx, (expected_code, expected_key) in enumerate(expected_keys):
        assert dims[idx]["code"] == expected_code
        assert dims[idx]["key"] == expected_key

def test_frozen_style_dna_canonical_structure():
    assert len(CANONICAL_STYLE_DNA) == 9
    assert CANONICAL_STYLE_DNA[0]["code"] == "D1"
    assert CANONICAL_STYLE_DNA[0]["key"] == "color_energy"
    assert CANONICAL_STYLE_DNA[1]["code"] == "D2"
    assert CANONICAL_STYLE_DNA[1]["key"] == "color_diversity"
    assert CANONICAL_STYLE_DNA[2]["code"] == "D3"
    assert CANONICAL_STYLE_DNA[2]["key"] == "contrast"
    assert CANONICAL_STYLE_DNA[3]["code"] == "D4"
    assert CANONICAL_STYLE_DNA[3]["key"] == "warmth"
    assert CANONICAL_STYLE_DNA[4]["code"] == "D5"
    assert CANONICAL_STYLE_DNA[4]["key"] == "visual_complexity"
    assert CANONICAL_STYLE_DNA[5]["code"] == "D6"
    assert CANONICAL_STYLE_DNA[5]["key"] == "structural_order"
    assert CANONICAL_STYLE_DNA[6]["code"] == "D7"
    assert CANONICAL_STYLE_DNA[6]["key"] == "rhythm_repetition"
    assert CANONICAL_STYLE_DNA[7]["code"] == "D8"
    assert CANONICAL_STYLE_DNA[7]["key"] == "focal_strength"
    assert CANONICAL_STYLE_DNA[8]["code"] == "D9"
    assert CANONICAL_STYLE_DNA[8]["key"] == "form_language"

@pytest.mark.asyncio
async def test_narrative_themes_contract_endpoint(client):
    response = await client.get("/api/v1/meta/narrative-themes")
    assert response.status_code == 200
    data = response.json()
    assert data["total_themes"] == 8
    themes = data["themes"]
    assert len(themes) == 8

    expected_keys = [
        ("N1", "nature_growth"),
        ("N2", "belonging_home"),
        ("N3", "journey_discovery"),
        ("N4", "continuity_connection"),
        ("N5", "balance_order"),
        ("N6", "renewal_transformation"),
        ("N7", "tradition_craft"),
        ("N8", "cultural_heritage"),
    ]

    for idx, (expected_code, expected_key) in enumerate(expected_keys):
        assert themes[idx]["code"] == expected_code
        assert themes[idx]["key"] == expected_key

def test_frozen_narrative_themes_canonical_structure():
    assert len(CANONICAL_NARRATIVE_THEMES) == 8
    assert CANONICAL_NARRATIVE_THEMES[0]["code"] == "N1"
    assert CANONICAL_NARRATIVE_THEMES[0]["key"] == "nature_growth"
    assert CANONICAL_NARRATIVE_THEMES[1]["code"] == "N2"
    assert CANONICAL_NARRATIVE_THEMES[1]["key"] == "belonging_home"
    assert CANONICAL_NARRATIVE_THEMES[2]["code"] == "N3"
    assert CANONICAL_NARRATIVE_THEMES[2]["key"] == "journey_discovery"
    assert CANONICAL_NARRATIVE_THEMES[3]["code"] == "N4"
    assert CANONICAL_NARRATIVE_THEMES[3]["key"] == "continuity_connection"
    assert CANONICAL_NARRATIVE_THEMES[4]["code"] == "N5"
    assert CANONICAL_NARRATIVE_THEMES[4]["key"] == "balance_order"
    assert CANONICAL_NARRATIVE_THEMES[5]["code"] == "N6"
    assert CANONICAL_NARRATIVE_THEMES[5]["key"] == "renewal_transformation"
    assert CANONICAL_NARRATIVE_THEMES[6]["code"] == "N7"
    assert CANONICAL_NARRATIVE_THEMES[6]["key"] == "tradition_craft"
    assert CANONICAL_NARRATIVE_THEMES[7]["code"] == "N8"
    assert CANONICAL_NARRATIVE_THEMES[7]["key"] == "cultural_heritage"
