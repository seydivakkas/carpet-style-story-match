"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

FastAPI Application Entry Point & Lifespan Bootstrap.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import CorrelationIDMiddleware, SecurityHeadersMiddleware, RateLimiterMiddleware
from app.db.session import dispose_db_engine
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting Carpet Style & Story Match API in {settings.APP_ENV} mode")
    yield
    logger.info("Shutting down API. Disposing database engine...")
    await dispose_db_engine()


app = FastAPI(
    title="Carpet Style & Story Match API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan
)

# 1. Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.TRUSTED_HOSTS
)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 4. Correlation ID Middleware
app.add_middleware(CorrelationIDMiddleware)

# 5. Rate Limiter Middleware
app.add_middleware(RateLimiterMiddleware)

# Include API v1 Router
app.include_router(api_v1_router)

# Mount /static for local image storage
from pathlib import Path
from fastapi.staticfiles import StaticFiles
_upload_dir = Path(settings.IMAGE_STORAGE_ROOT).resolve()
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_upload_dir)), name="static")


# Global exception handler to prevent traceback leakage in 500 responses
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred."
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=(settings.APP_ENV == "development")
    )
