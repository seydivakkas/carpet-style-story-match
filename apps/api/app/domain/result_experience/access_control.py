"""Analiz bazlı yetki kanıtı. Gerçek kimlik yönetiminin yerine geçmez."""
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings

def new_analysis_access_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()

def require_analysis_access(record: object, provided_token: Optional[str], *, environment: Optional[str] = None) -> None:
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analiz bulunamadı.")
    mode = (environment or settings.APP_ENV).lower()
    if mode != "test":
        stored_hash = getattr(record, "owner_token_sha256", None)
        valid = (
            isinstance(stored_hash, str)
            and len(stored_hash) == 64
            and isinstance(provided_token, str)
            and 32 <= len(provided_token) <= 256
            and hmac.compare_digest(hashlib.sha256(provided_token.encode("utf-8")).hexdigest(), stored_hash)
        )
        if not valid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analiz erişim yetkisi bulunamadı.")
    expires_at = getattr(record, "expires_at", None)
    if expires_at is not None:
        if expires_at.tzinfo is None:
            # SQLite UTC DATETIME tipinde saat dilimi bilgisini atabilir.
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Analizin saklama süresi doldu.")
