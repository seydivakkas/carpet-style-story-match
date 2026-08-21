"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Unit tests for Production Configuration Fail-Fast Validation.
"""
import pytest
from app.core.config import Settings


def test_development_config_valid():
    s = Settings(APP_ENV="development", DEBUG=True, CORS_ORIGINS=["*"])
    # Development does not raise errors for wildcard CORS or debug
    s.validate_production_config()


def test_production_config_valid():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["example.com", "api.example.com"],
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    s.validate_production_config()


def test_production_rejects_debug():
    s = Settings(
        APP_ENV="production",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["example.com"],
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    with pytest.raises(ValueError, match="DEBUG must be False in production mode"):
        s.validate_production_config()


def test_production_rejects_development_admin():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["example.com"],
        MOTIF_REVIEW_ACCESS_MODE="DEVELOPMENT_ADMIN"
    )
    with pytest.raises(ValueError, match="MOTIF_REVIEW_ACCESS_MODE cannot be DEVELOPMENT_ADMIN"):
        s.validate_production_config()


def test_production_rejects_wildcard_cors():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["*"],
        TRUSTED_HOSTS=["example.com"],
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        s.validate_production_config()


def test_production_rejects_wildcard_trusted_hosts():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["*"],
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    with pytest.raises(ValueError, match="Wildcard trusted host"):
        s.validate_production_config()


def test_production_rejects_default_dev_password():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:carpet_password@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["example.com"],
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    with pytest.raises(ValueError, match="Default development database password is forbidden"):
        s.validate_production_config()


def test_production_rejects_missing_s3_credentials():
    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://carpet_user:secure_prod_pass_123@postgres:5432/carpet_db",
        CORS_ORIGINS=["https://example.com"],
        TRUSTED_HOSTS=["example.com"],
        STORAGE_BACKEND="s3",
        S3_ACCESS_KEY=None,
        MOTIF_REVIEW_ACCESS_MODE="AUTHENTICATED"
    )
    with pytest.raises(ValueError, match="S3 credentials"):
        s.validate_production_config()
