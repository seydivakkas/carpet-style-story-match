"""İşlem sürerken silme kaynak yarışı ve sahipsiz sonuç oluşumunu engeller."""
import uuid
import pytest
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum
from app.domain.result_experience.access_control import new_analysis_access_token

@pytest.mark.asyncio
async def test_delete_processing_analysis_returns_409_without_deleting_db(client, db_session):
    access_token, digest = new_analysis_access_token()
    record = UploadAnalysisModel(
        id=uuid.uuid4(), owner_token_sha256=digest, original_sha256="x" * 64,
        mime_type="image/jpeg", quality_status="PENDING",
        status=UploadAnalysisStatusEnum.PROCESSING
    )
    db_session.add(record)
    await db_session.commit()
    response = await client.delete(
        f"/api/v1/upload-analysis/{record.id}",
        headers={"X-Analysis-Token":access_token},
    )
    assert response.status_code == 409
    still_there = await db_session.get(UploadAnalysisModel, record.id)
    assert still_there is not None
    assert still_there.status == UploadAnalysisStatusEnum.PROCESSING
