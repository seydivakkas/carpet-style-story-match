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


# Dört farklı REST uç noktası aynı kaynak sahipliği kapısını kullanır.
@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["status", "result", "image", "delete"])
async def test_unauthorized_cannot_retrieve_or_delete_any_analysis_resource(monkeypatch, target):
    import uuid
    from app.domain.result_experience import access_control
    from app.api.v1 import result_experience, upload_analysis

    token, digest = new_analysis_access_token()
    record = SimpleNamespace(id=uuid.uuid4(), owner_token_sha256=digest, image_path="secret.jpg")

    class FakeRows:
        def scalar_one_or_none(self):
            return record

    class FakeDatabase:
        async def execute(self, _query):
            return FakeRows()
        async def commit(self):
            raise AssertionError("Yetkisiz istekte commit olmamalı")

    monkeypatch.setattr(access_control.settings, "APP_ENV", "production")
    handlers = {
        "status": result_experience.get_analysis_status,
        "result": result_experience.get_unified_result_by_id,
        "image": upload_analysis.get_analysis_image,
        "delete": upload_analysis.delete_analysis_record,
    }
    with pytest.raises(HTTPException) as error:
        await handlers[target](record.id, x_analysis_token="yanlis-erisim-anahtari"*4, db=FakeDatabase())
    assert error.value.status_code == 403


def test_development_mode_does_not_bypass_resource_ownership():
    token, digest = new_analysis_access_token()
    with pytest.raises(HTTPException) as ex:
        require_analysis_access(SimpleNamespace(owner_token_sha256=digest), None, environment="development")
    assert ex.value.status_code == 403
    require_analysis_access(SimpleNamespace(owner_token_sha256=digest), token, environment="development")
