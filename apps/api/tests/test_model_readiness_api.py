"""Bilimsel kabul verisinin güvenli ve dürüst durum sözleşmesi."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.api.v1.model_readiness import audit_runtime_evidence
from app.main import app

def test_no_artifacts_cannot_pass_model_gate(tmp_path: Path):
    result = audit_runtime_evidence(tmp_path)
    assert result.status == "HOLD"
    assert result.approved_for_production is False
    assert result.independent_holdout_verified is False
    assert result.available_artifacts == 0
    assert result.checked_artifacts == 9
    assert len(result.missing_artifacts) == 9

def test_file_presence_does_not_imply_valid_model(tmp_path: Path):
    (tmp_path / "artifacts/v2-09c/models/R0").mkdir(parents=True)
    result = audit_runtime_evidence(tmp_path)
    assert result.available_artifacts == 1
    assert result.model_quality == "NOT_VALIDATED"
    assert result.status == "HOLD"

def test_public_endpoint_does_not_reveal_absolute_paths(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CARPET_EVIDENCE_ROOT", str(tmp_path))
    response = TestClient(app).get("/api/v1/system/model-acceptance")
    assert response.status_code == 200
    payload = response.json()
    assert payload["approved_for_production"] is False
    assert str(tmp_path) not in response.text
    assert payload["missing_artifacts"]
