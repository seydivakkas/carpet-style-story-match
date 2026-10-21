"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production Hardened Image Storage Subsystem.
Supports Local Filesystem Storage and S3/MinIO Object Storage abstraction.
"""
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.domain.images.exceptions import ImageStorageFailedError


class ImageStorage(ABC):
    @abstractmethod
    def save_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID, file_bytes: bytes, extension: str) -> str:
        """Saves image bytes and returns server-managed storage key."""
        pass

    @abstractmethod
    def get_image_bytes(self, storage_key: str) -> bytes:
        """Retrieves image bytes from storage key."""
        pass

    @abstractmethod
    def image_exists(self, storage_key: str) -> bool:
        """Return True if image file exists in storage."""
        pass

    @abstractmethod
    def delete_image(self, storage_key: str) -> None:
        """Deletes image file from storage."""
        pass

    @abstractmethod
    def delete_carpet_dir(self, carpet_id: uuid.UUID) -> None:
        """Deletes entire carpet directory and contained files."""
        pass


class LocalImageStorage(ImageStorage):
    def __init__(self, root_dir: Optional[str] = None):
        self.root_path = Path(root_dir or settings.IMAGE_STORAGE_ROOT).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> Path:
        clean_key = storage_key.lstrip("/\\")
        target_path = (self.root_path / clean_key).resolve()

        if not target_path.is_relative_to(self.root_path):
            raise ImageStorageFailedError("Path traversal detected in storage key")
        return target_path

    def save_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID, file_bytes: bytes, extension: str) -> str:
        clean_ext = extension.lstrip(".").lower()
        if not clean_ext:
            clean_ext = "jpg"
        
        rel_key = f"carpets/{carpet_id}/{image_id}.{clean_ext}"
        target_path = self._resolve_safe_path(rel_key)
        
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(file_bytes)
            return rel_key
        except Exception as e:
            raise ImageStorageFailedError(f"Failed to write file to disk: {e}") from e

    def get_image_bytes(self, storage_key: str) -> bytes:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.exists() or not target_path.is_file():
            raise ImageStorageFailedError(f"Storage file '{storage_key}' does not exist.")
        try:
            with open(target_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise ImageStorageFailedError(f"Failed to read file from disk: {e}") from e

    def image_exists(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(storage_key)
            return target_path.exists() and target_path.is_file()
        except Exception:
            return False

    def delete_image(self, storage_key: str) -> None:
        """Silme hatalarını üst katmana bildir; veritabanı silinmeden önce kontrol edilir."""
        target_path = self._resolve_safe_path(storage_key)
        if target_path.exists() and target_path.is_file():
            try:
                target_path.unlink()
            except OSError as exc:
                raise ImageStorageFailedError("Görsel dosyası silinemedi.") from exc

    def delete_carpet_dir(self, carpet_id: uuid.UUID) -> None:
        rel_dir = f"carpets/{carpet_id}"
        try:
            target_dir = self._resolve_safe_path(rel_dir)
            if target_dir.exists() and target_dir.is_dir():
                shutil.rmtree(target_dir, ignore_errors=True)
        except Exception:
            pass


class S3ImageStorage(ImageStorage):
    """Gerçek S3 uyumlu depolama; kayıp veri durumunda başarı döndürmez."""

    def __init__(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise ImageStorageFailedError("S3 kullanımı için boto3 bağımlılığı gereklidir.") from exc
        if not settings.S3_BUCKET_NAME or not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
            raise ImageStorageFailedError("S3 bucket ve kimlik bilgileri tanımlanmalı.")
        self.bucket = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_SECURE,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def _validate_key(storage_key: str) -> str:
        key = storage_key.replace("\\", "/")
        if (not key or key.startswith("/") or any(
            part in ("", ".", "..") for part in key.split("/")
        )):
            raise ImageStorageFailedError("Geçersiz nesne anahtarı.")
        return key

    def save_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID, file_bytes: bytes, extension: str) -> str:
        clean_ext = extension.lstrip(".").lower() or "jpg"
        if clean_ext not in ("jpg", "jpeg", "png", "webp"):
            raise ImageStorageFailedError("Geçersiz görsel uzantısı.")
        key = self._validate_key(f"carpets/{carpet_id}/{image_id}.{clean_ext}")
        content_type = "image/jpeg" if clean_ext in ("jpg", "jpeg") else f"image/{clean_ext}"
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=file_bytes, ContentType=content_type)
        except Exception as exc:
            raise ImageStorageFailedError("S3 nesne yüklemesi başarısız.") from exc
        return key

    def get_image_bytes(self, storage_key: str) -> bytes:
        key = self._validate_key(storage_key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            with response["Body"] as body:
                return body.read()
        except Exception as exc:
            raise ImageStorageFailedError("S3 nesnesi okunamadı.") from exc

    def image_exists(self, storage_key: str) -> bool:
        key = self._validate_key(storage_key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:
            from botocore.exceptions import ClientError
            if isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise ImageStorageFailedError("S3 varlık kontrolü başarısız.") from exc

    def delete_image(self, storage_key: str) -> None:
        key = self._validate_key(storage_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise ImageStorageFailedError("S3 nesnesi silinemedi.") from exc

    def delete_carpet_dir(self, carpet_id: uuid.UUID) -> None:
        prefix = f"carpets/{carpet_id}/"
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                items = page.get("Contents", [])
                if items:
                    self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": [{"Key": item["Key"]} for item in items], "Quiet": True},
                    )
        except Exception as exc:
            raise ImageStorageFailedError("S3 klasör nesneleri temizlenemedi.") from exc


def get_image_storage() -> ImageStorage:
    """Factory function for acquiring configured ImageStorage backend."""
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3ImageStorage()
    return LocalImageStorage()
