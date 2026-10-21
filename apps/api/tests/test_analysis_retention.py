"""Analiz saklama süresi, erişim 410 ve gerçek DB silme davranışı."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum
from app.domain.result_experience.retention import cleanup_expired_analyses
from app.domain.result_experience.access_control import new_analysis_access_token, require_analysis_access

class FakeStorage:
    def __init__(self, fails=False):
        self.deleted = []
        self.fails = fails
    def delete_image(self, key):
        if self.fails:
            raise OSError("Disk silme hatası")
        self.deleted.append(key)

def new_row(expiry, key):
    token, digest = new_analysis_access_token()
    return UploadAnalysisModel(
        id=uuid.uuid4(), original_sha256="0" * 64, owner_token_sha256=digest,
        status=UploadAnalysisStatusEnum.COMPLETED, mime_type="image/jpeg",
        quality_status="PASS", image_path=key, expires_at=expiry,
    ), token

@pytest.mark.asyncio
async def test_retention_only_removes_expired_new_records(db_session):
    now = datetime.now(timezone.utc)
    old, _ = new_row(now - timedelta(days=1), "expired.jpg")
    active, _ = new_row(now + timedelta(days=3), "active.jpg")
    legacy, _ = new_row(None, "legacy.jpg")
    db_session.add_all([old, active, legacy])
    await db_session.commit()
    storage = FakeStorage()
    result = await cleanup_expired_analyses(db_session, storage, now=now)
    assert result == {"deleted": 1, "failed": 0}
    assert storage.deleted == ["expired.jpg"]
    records = (await db_session.execute(select(UploadAnalysisModel))).scalars().all()
    assert {r.id for r in records} == {active.id, legacy.id}

@pytest.mark.asyncio
async def test_retention_storage_error_keeps_record_for_retry(db_session):
    now = datetime.now(timezone.utc)
    old, _ = new_row(now - timedelta(seconds=1), "fail.jpg")
    db_session.add(old)
    old_id = old.id  # Rollback sonrasında ORM nesnesinin expired attribute erişimi DB IO tetikleyebilir.
    await db_session.commit()
    result = await cleanup_expired_analyses(db_session, FakeStorage(fails=True), now=now)
    assert result == {"deleted": 0, "failed": 1}
    assert (await db_session.get(UploadAnalysisModel, old_id)) is not None

def test_expired_token_returns_410_after_owner_check():
    now = datetime.now(timezone.utc)
    token, digest = new_analysis_access_token()
    old = SimpleNamespace(owner_token_sha256=digest, expires_at=now - timedelta(seconds=1))
    with pytest.raises(HTTPException) as expired:
        require_analysis_access(old, token, environment="production")
    assert expired.value.status_code == 410
    with pytest.raises(HTTPException) as forbidden:
        require_analysis_access(old, "wrong" * 12, environment="production")
    assert forbidden.value.status_code == 403
