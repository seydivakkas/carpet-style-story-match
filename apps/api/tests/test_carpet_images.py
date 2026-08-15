import io
import os
import uuid
import pytest
from PIL import Image
from pathlib import Path
from app.core.config import settings

def create_dummy_image_bytes(format_name: str = "JPEG", size: tuple = (200, 200), color: tuple = (255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=format_name)
    return buf.getvalue()

@pytest.fixture
async def sample_carpet_id(client):
    res = await client.post("/api/v1/carpets", json={"name": "Image Test Carpet"})
    assert res.status_code == 201
    return res.json()["id"]

@pytest.mark.asyncio
async def test_upload_valid_jpeg_success(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("JPEG", (200, 250), (200, 100, 50))
    files = {"file": ("carpet_front.jpg", img_bytes, "image/jpeg")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["carpet_id"] == sample_carpet_id
    assert data["original_filename"] == "carpet_front.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["width_px"] == 200
    assert data["height_px"] == 250
    assert data["is_primary"] is True
    assert "content_url" in data
    assert "C:\\" not in data["content_url"]

@pytest.mark.asyncio
async def test_upload_valid_png_and_primary_flag(client, sample_carpet_id):
    # Upload first image (primary)
    bytes1 = create_dummy_image_bytes("JPEG", (300, 300), (0, 255, 0))
    res1 = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("img1.jpg", bytes1, "image/jpeg")})
    assert res1.status_code == 201
    assert res1.json()["is_primary"] is True

    # Upload second image (non-primary)
    bytes2 = create_dummy_image_bytes("PNG", (350, 350), (0, 0, 255))
    res2 = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("img2.png", bytes2, "image/png")})
    assert res2.status_code == 201
    assert res2.json()["is_primary"] is False

@pytest.mark.asyncio
async def test_upload_valid_webp_success(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("WEBP", (400, 400), (128, 128, 128))
    files = {"file": ("carpet_side.webp", img_bytes, "image/webp")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["content_type"] == "image/webp"

@pytest.mark.asyncio
async def test_upload_fake_corrupt_image(client, sample_carpet_id):
    fake_bytes = b"NOT_AN_IMAGE_THIS_IS_PLAIN_TEXT"
    files = {"file": ("fake.jpg", fake_bytes, "image/jpeg")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMAGE_DECODE_FAILED"

@pytest.mark.asyncio
async def test_upload_unsupported_media_type(client, sample_carpet_id):
    pdf_bytes = b"%PDF-1.4 sample content"
    files = {"file": ("document.pdf", pdf_bytes, "application/pdf")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "IMAGE_UNSUPPORTED_MEDIA_TYPE"

@pytest.mark.asyncio
async def test_upload_too_small_dimensions(client, sample_carpet_id):
    small_bytes = create_dummy_image_bytes("JPEG", (50, 50))  # < 128x128
    files = {"file": ("tiny.jpg", small_bytes, "image/jpeg")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IMAGE_DIMENSIONS_TOO_SMALL"

@pytest.mark.asyncio
async def test_upload_path_traversal_filename_safety(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("JPEG", (250, 250))
    files = {"file": ("../../evil_path_traversal.jpg", img_bytes, "image/jpeg")}

    response = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "../../evil_path_traversal.jpg"
    
    # Verify file is stored in server-generated path
    image_id = data["id"]
    storage_root = Path(settings.IMAGE_STORAGE_ROOT).resolve()
    expected_file = storage_root / "carpets" / sample_carpet_id / f"{image_id}.jpg"
    assert expected_file.exists()

@pytest.mark.asyncio
async def test_upload_duplicate_image_conflict(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("JPEG", (300, 300), (100, 100, 100))

    res1 = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("img.jpg", img_bytes, "image/jpeg")})
    assert res1.status_code == 201

    res2 = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("img_copy.jpg", img_bytes, "image/jpeg")})
    assert res2.status_code == 409
    assert res2.json()["detail"]["code"] == "IMAGE_DUPLICATE"

@pytest.mark.asyncio
async def test_get_image_metadata_and_content_stream(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("PNG", (220, 220), (50, 50, 200))
    post_res = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("test.png", img_bytes, "image/png")})
    image_id = post_res.json()["id"]

    # Get metadata
    meta_res = await client.get(f"/api/v1/carpets/{sample_carpet_id}/images/{image_id}")
    assert meta_res.status_code == 200
    assert meta_res.json()["id"] == image_id

    # Stream content
    content_res = await client.get(f"/api/v1/carpets/{sample_carpet_id}/images/{image_id}/content")
    assert content_res.status_code == 200
    assert content_res.headers["content-type"] == "image/png"
    assert len(content_res.content) > 0

@pytest.mark.asyncio
async def test_delete_carpet_image_cleans_file(client, sample_carpet_id):
    img_bytes = create_dummy_image_bytes("JPEG", (200, 200), (80, 80, 80))
    post_res = await client.post(f"/api/v1/carpets/{sample_carpet_id}/images", files={"file": ("to_del.jpg", img_bytes, "image/jpeg")})
    image_id = post_res.json()["id"]

    storage_root = Path(settings.IMAGE_STORAGE_ROOT).resolve()
    file_path = storage_root / "carpets" / sample_carpet_id / f"{image_id}.jpg"
    assert file_path.exists()

    del_res = await client.delete(f"/api/v1/carpets/{sample_carpet_id}/images/{image_id}")
    assert del_res.status_code == 204

    # Verify file is deleted on disk
    assert not file_path.exists()

@pytest.mark.asyncio
async def test_delete_carpet_cleans_all_image_files(client):
    carpet_res = await client.post("/api/v1/carpets", json={"name": "Carpet To Delete"})
    carpet_id = carpet_res.json()["id"]

    b1 = create_dummy_image_bytes("JPEG", (200, 200), (10, 10, 10))
    b2 = create_dummy_image_bytes("PNG", (200, 200), (20, 20, 20))

    r1 = await client.post(f"/api/v1/carpets/{carpet_id}/images", files={"file": ("1.jpg", b1, "image/jpeg")})
    r2 = await client.post(f"/api/v1/carpets/{carpet_id}/images", files={"file": ("2.png", b2, "image/png")})

    img1_path = Path(settings.IMAGE_STORAGE_ROOT).resolve() / "carpets" / carpet_id / f"{r1.json()['id']}.jpg"
    img2_path = Path(settings.IMAGE_STORAGE_ROOT).resolve() / "carpets" / carpet_id / f"{r2.json()['id']}.png"

    assert img1_path.exists()
    assert img2_path.exists()

    del_carpet_res = await client.delete(f"/api/v1/carpets/{carpet_id}")
    assert del_carpet_res.status_code == 204

    # Verify all carpet image files on disk were cleaned up
    assert not img1_path.exists()
    assert not img2_path.exists()
