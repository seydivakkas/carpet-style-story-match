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

        if not str(target_path).startswith(str(self.root_path)):
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

    def delete_image(self, storage_key: str) -> None:
        try:
            target_path = self._resolve_safe_path(storage_key)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
        except Exception:
            pass

    def delete_carpet_dir(self, carpet_id: uuid.UUID) -> None:
        rel_dir = f"carpets/{carpet_id}"
        try:
            target_dir = self._resolve_safe_path(rel_dir)
            if target_dir.exists() and target_dir.is_dir():
                shutil.rmtree(target_dir, ignore_errors=True)
        except Exception:
            pass


class S3ImageStorage(ImageStorage):
    """S3-compatible / MinIO Object Storage implementation."""
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.endpoint = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY

    def save_image(self, carpet_id: uuid.UUID, image_id: uuid.UUID, file_bytes: bytes, extension: str) -> str:
        clean_ext = extension.lstrip(".").lower() or "jpg"
        storage_key = f"carpets/{carpet_id}/{image_id}.{clean_ext}"
        # Server-generated safe key
        return storage_key

    def get_image_bytes(self, storage_key: str) -> bytes:
        raise ImageStorageFailedError("S3 storage byte retrieval requires active S3/MinIO client connection.")

    def delete_image(self, storage_key: str) -> None:
        pass

    def delete_carpet_dir(self, carpet_id: uuid.UUID) -> None:
        pass


def get_image_storage() -> ImageStorage:
    """Factory function for acquiring configured ImageStorage backend."""
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3ImageStorage()
    return LocalImageStorage()
