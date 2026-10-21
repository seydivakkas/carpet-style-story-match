"""İki görsel yükleme uç noktasında aşırı büyük gövde reddi."""
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.upload_analysis import get_settings as motif_settings
from app.api.v1.result_experience import get_settings as result_settings
from app.core.config import Settings

def test_motif_detect_rejects_oversized_image_without_provider_call():
    app.dependency_overrides[motif_settings] = lambda: Settings(MAX_IMAGE_UPLOAD_BYTES=4)
    try:
        with TestClient(app) as client:
            result = client.post("/api/v1/upload-analysis/motif-detect",
                files={"file": ("oversized.jpg", b"not-an-image", "image/jpeg")})
        assert result.status_code == 413
    finally:
        app.dependency_overrides.pop(motif_settings, None)
