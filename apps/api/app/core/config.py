"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production-hardened application configuration module.
Provides environment-aware settings and fail-fast production validation.
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_READINESS_VERSION = "production-readiness-v1"
RELEASE_OPERATIONS_VERSION = "release-operations-v1"


class Settings(BaseSettings):
    # Environment & Host Config
    APP_ENV: str = Field(default="development", description="Environment mode: development, test, or production")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    API_HOST: str = Field(default="0.0.0.0", description="Host interface binding")
    API_PORT: int = Field(default=8000, description="API server port")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://carpet_user:carpet_password@localhost:5432/carpet_db",
        description="Async SQLAlchemy database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=10, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="SQLAlchemy connection pool max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="SQLAlchemy connection pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=1800, description="SQLAlchemy connection pool recycle interval in seconds")
    DB_POOL_PRE_PING: bool = Field(default=True, description="Enable SQLAlchemy connection pool pre-ping")

    # Security & CORS Configuration
    WEB_ORIGIN: str = Field(default="http://localhost:3000", description="Primary web frontend origin")
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ],
        description="Allowed CORS origins"
    )
    TRUSTED_HOSTS: List[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0", "api", "web", "testserver", "test"], description="Allowed HTTP host headers")

    # Image Storage Configuration
    STORAGE_BACKEND: str = Field(default="local", description="Image storage backend: local or s3")
    IMAGE_STORAGE_ROOT: str = Field(default="./data/uploads", description="Local image storage directory")
    MAX_IMAGE_UPLOAD_BYTES: int = Field(default=15 * 1024 * 1024, description="Max upload size in bytes (15MB)")
    MIN_IMAGE_WIDTH: int = Field(default=128, description="Minimum allowed image width")
    MIN_IMAGE_HEIGHT: int = Field(default=128, description="Minimum allowed image height")
    MAX_IMAGE_WIDTH: int = Field(default=12000, description="Maximum allowed image width")
    MAX_IMAGE_HEIGHT: int = Field(default=12000, description="Maximum allowed image height")
    MAX_IMAGE_PIXELS: int = Field(default=80_000_000, description="Maximum allowed total pixel count")

    # Optional S3 / MinIO Storage Configuration
    S3_ENDPOINT_URL: Optional[str] = Field(default=None, description="S3 / MinIO endpoint URL")
    S3_BUCKET_NAME: Optional[str] = Field(default="carpet-assets", description="S3 / MinIO bucket name")

    # VLM / Vision-Language Model Configuration (V2-03)
    MOTIF_VLM_PROVIDER: str = Field(default="DISABLED", description="Provider mode: DISABLED, LOCAL_VLLM, REMOTE_OPENAI_COMPATIBLE, or TEST_FIXTURE")
    MOTIF_VLM_BASE_URL: Optional[str] = Field(default=None, description="Server-side VLM endpoint base URL")
    MOTIF_VLM_MODEL: str = Field(default="Qwen/Qwen2-VL-7B-Instruct", description="VLM model identifier")
    MOTIF_VLM_API_KEY: Optional[str] = Field(default=None, description="Server-side API key for remote VLM provider")
    MOTIF_VLM_TIMEOUT_SECONDS: float = Field(default=30.0, description="VLM inference HTTP request timeout in seconds")
    MOTIF_VLM_MAX_RETRIES: int = Field(default=1, description="Max schema-correction retries on malformed VLM output")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 secret key")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    S3_SECURE: bool = Field(default=True, description="S3 HTTPS requirement")

    # Rate Limiting Configuration
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, description="Max requests per minute per IP for sensitive endpoints")
    ENABLE_RATE_LIMITER_IN_TEST: bool = Field(default=False, description="Flag to explicitly enable rate limiter in test mode")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_config(self) -> None:
        """
        Validates settings for production environment mode.
        Raises ValueError immediately if invalid/unsafe configuration is detected.
        """
        if self.APP_ENV.lower() != "production":
            return

        if self.DEBUG:
            raise ValueError("Production configuration violation: DEBUG must be False in production mode.")

        if "sqlite" in self.DATABASE_URL.lower():
            raise ValueError("Production configuration violation: SQLite database is forbidden in production mode. Use PostgreSQL.")

        if "*" in self.CORS_ORIGINS or (isinstance(self.CORS_ORIGINS, str) and self.CORS_ORIGINS == "*"):
            raise ValueError("Production configuration violation: Wildcard CORS origin '*' is forbidden in production.")

        if "*" in self.TRUSTED_HOSTS or (isinstance(self.TRUSTED_HOSTS, str) and self.TRUSTED_HOSTS == "*"):
            raise ValueError("Production configuration violation: Wildcard trusted host '*' is forbidden in production.")

        if "carpet_password" in self.DATABASE_URL:
            raise ValueError("Production configuration violation: Default development database password is forbidden in production.")

        if self.STORAGE_BACKEND.lower() == "s3":
            if not self.S3_ACCESS_KEY or not self.S3_SECRET_KEY or not self.S3_BUCKET_NAME:
                raise ValueError("Production configuration violation: S3 credentials (access_key, secret_key, bucket_name) required when STORAGE_BACKEND=s3.")


settings = Settings()
# Run fail-fast production config validation on initialization
if settings.APP_ENV.lower() == "production":
    settings.validate_production_config()
