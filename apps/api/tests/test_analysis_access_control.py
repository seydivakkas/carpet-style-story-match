"""Analiz bazlı erişim kanıtı için üretim negatif testleri."""
import hashlib
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.domain.result_experience.access_control import new_analysis_access_token, require_analysis_access

def test_random_token_persists_only_hash():
    a, ah = new_analysis_access_token()
    b, bh = new_analysis_access_token()
    assert a != b and ah != bh
    assert ah == hashlib.sha256(a.encode("utf-8")).hexdigest()
    assert a not in ah

@pytest.mark.parametrize("token", [None, "", "short", "wrong-" * 15, "x" * 257])
def test_production_deny_invalid_token(token):
    _, stored = new_analysis_access_token()
    with pytest.raises(HTTPException) as ex:
        require_analysis_access(SimpleNamespace(owner_token_sha256=stored), token, environment="production")
    assert ex.value.status_code == 403

def test_production_accepts_only_correct_token():
    token, stored = new_analysis_access_token()
    require_analysis_access(SimpleNamespace(owner_token_sha256=stored), token, environment="production")

def test_production_denies_legacy_missing_hash():
    with pytest.raises(HTTPException) as ex:
        require_analysis_access(SimpleNamespace(owner_token_sha256=None), "a"*64, environment="production")
    assert ex.value.status_code == 403

def test_nonexistent_returns_404():
    with pytest.raises(HTTPException) as ex:
        require_analysis_access(None, None, environment="production")
    assert ex.value.status_code == 404
