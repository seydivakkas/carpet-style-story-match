"""Geçici, gerçek MinIO servisiyle S3 nesne yaşam döngüsünü doğrular.

Test bucket'ı için servis adresi dışına erişim yoktur. Üretim görselleri kullanılmaz.
"""
import time
import uuid
from botocore.exceptions import BotoCoreError, ClientError
from app.domain.images.storage import S3ImageStorage
from app.domain.images.exceptions import ImageStorageFailedError

def main() -> None:
    last_error = None
    storage = S3ImageStorage()
    for _ in range(30):
        try:
            storage.client.list_buckets()
            break
        except (BotoCoreError, ClientError, OSError) as exc:
            last_error = exc
            time.sleep(1)
    else:
        raise RuntimeError("MinIO sağlıklı başlamadı.") from last_error

    try:
        storage.client.create_bucket(Bucket=storage.bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise

    carpet = uuid.uuid4()
    key = storage.save_image(carpet, uuid.uuid4(), b"test-image-binary-no-personal-data", "jpg")
    try:
        assert storage.image_exists(key)
        assert storage.get_image_bytes(key) == b"test-image-binary-no-personal-data"
        try:
            storage.get_image_bytes("../private/file.jpg")
        except ImageStorageFailedError:
            pass
        else:
            raise AssertionError("S3 dizin dışına çıkış reddedilmedi.")
    finally:
        storage.delete_image(key)
    assert not storage.image_exists(key)

    key1 = storage.save_image(carpet, uuid.uuid4(), b"test-1", "png")
    key2 = storage.save_image(carpet, uuid.uuid4(), b"test-2", "webp")
    storage.delete_carpet_dir(carpet)
    assert not storage.image_exists(key1)
    assert not storage.image_exists(key2)
    print("MINIO_S3_REAL_OBJECT_LIFECYCLE_PASS")

if __name__ == "__main__":
    main()
