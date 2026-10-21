"""Görsel depolama sözleşmesi ve kullanıcı verisi temizliği testleri."""
import uuid
import pytest
from app.domain.images.storage import LocalImageStorage, S3ImageStorage
from app.domain.images.exceptions import ImageStorageFailedError

def test_local_write_read_delete(tmp_path):
    store = LocalImageStorage(str(tmp_path))
    aid = uuid.uuid4()
    key = store.save_image(aid, aid, b"test-image", "jpg")
    assert store.image_exists(key)
    assert store.get_image_bytes(key) == b"test-image"
    store.delete_image(key)
    assert not store.image_exists(key)

def test_local_prefix_traversal_rejected(tmp_path):
    store = LocalImageStorage(str(tmp_path / "images"))
    with pytest.raises(ImageStorageFailedError):
        store.get_image_bytes("../images-backup/secret.jpg")

def test_s3_rejects_unsafe_keys():
    for key in ("../private", "/root/file", "carpets//file", "carpets/./file", ""):
        with pytest.raises(ImageStorageFailedError):
            S3ImageStorage._validate_key(key)

class FakeS3:
    def __init__(self):
        self.data = {}
    def put_object(self, **kw):
        self.data[kw["Key"]] = kw["Body"]
    def get_object(self, **kw):
        import io
        return {"Body": io.BytesIO(self.data[kw["Key"]])}
    def head_object(self, **kw):
        if kw["Key"] not in self.data:
            raise RuntimeError("not found")
    def delete_object(self, **kw):
        self.data.pop(kw["Key"], None)

def test_s3_roundtrip_without_network():
    store = object.__new__(S3ImageStorage)
    store.bucket = "test"
    store.client = FakeS3()
    uid = uuid.uuid4()
    key = store.save_image(uid, uid, b"JPEG", "jpg")
    assert store.get_image_bytes(key) == b"JPEG"
    assert store.image_exists(key)
    store.delete_image(key)
    assert not key in store.client.data
    with pytest.raises(ImageStorageFailedError):
        store.get_image_bytes(key)
