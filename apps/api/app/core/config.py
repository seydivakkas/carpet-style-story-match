from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://carpet_user:carpet_password@localhost:5432/carpet_db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WEB_ORIGIN: str = "http://localhost:3000"

    # Image Upload & Validation Configuration
    IMAGE_STORAGE_ROOT: str = "./data/uploads"
    MAX_IMAGE_UPLOAD_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MIN_IMAGE_WIDTH: int = 128
    MIN_IMAGE_HEIGHT: int = 128
    MAX_IMAGE_WIDTH: int = 12000
    MAX_IMAGE_HEIGHT: int = 12000
    MAX_IMAGE_PIXELS: int = 80_000_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
