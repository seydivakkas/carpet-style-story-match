"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production Hardening Middleware Suite:
- Correlation ID (X-Request-ID) validation & propagation
- Security Headers enforcement
- In-memory bounded rate limiting with HTTP 429 & Retry-After
"""
import re
import time
import uuid
from app.core.shared_rate_limit import acquire_redis_quota
from typing import Dict, List
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.logging import request_id_ctx, logger

# Request ID validation pattern (alphanumeric, hyphen, underscore, 1-64 chars)
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# In-memory rate limiter bucket storage: IP -> List[timestamps]
_rate_limit_store: Dict[str, List[float]] = {}


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Validates or generates X-Request-ID, binds it to contextvars and logging,
    and returns X-Request-ID in response headers.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            req_id = incoming_id
        else:
            req_id = f"req_{uuid.uuid4().hex}"

        token = request_id_ctx.set(req_id)
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id

            logger.info(
                f"{request.method} {request.url.path} {response.status_code} - {duration_ms}ms"
            )
            return response
        finally:
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces standard security response headers."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory bounded rate limiter keyed by client IP.
    Exempts operational health endpoints.
    """
    EXEMPT_PATHS = {
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/health",
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json"
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # In test environment, bypass rate limiting unless explicitly enabled for rate limit testing
        if (
            settings.APP_ENV.lower() == "test" and not settings.ENABLE_RATE_LIMITER_IN_TEST
        ) or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if settings.RATE_LIMIT_BACKEND.lower() == "redis":
            try:
                if not settings.REDIS_URL:
                    raise RuntimeError("Paylaşımlı hız sınırı Redis URL yapılandırılmamış.")
                allowed = await acquire_redis_quota(
                    settings.REDIS_URL, client_ip, max_requests=settings.RATE_LIMIT_PER_MINUTE
                )
            except Exception:
                logger.exception("Paylaşımlı hız sınırı devre dışı kaldı; üretimde geçiş izni verilmiyor.")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail":{"code":"RATE_LIMIT_UNAVAILABLE",
                                       "message":"Request throttling service is unavailable."}}
                )
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After":"60"},
                    content={"detail":{"code":"RATE_LIMIT_EXCEEDED",
                                       "message":"Rate limit exceeded. Please try again later."}}
                )
            return await call_next(request)
        if settings.APP_ENV.lower() == "production":
            # Çok işçi dağıtımında in-memory hız sınırı güvenli değildir.
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail":{"code":"RATE_LIMIT_UNAVAILABLE",
                                   "message":"Shared rate limiting is required in production."}}
            )

        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        timestamps = _rate_limit_store.get(client_ip, [])
        valid_timestamps = [t for t in timestamps if t > window_start]

        if len(valid_timestamps) >= settings.RATE_LIMIT_PER_MINUTE:
            _rate_limit_store[client_ip] = valid_timestamps
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
                content={
                    "detail": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please try again later."
                    }
                }
            )

        valid_timestamps.append(now)
        _rate_limit_store[client_ip] = valid_timestamps
        return await call_next(request)


def reset_rate_limiter() -> None:
    """Helper to clear rate limit store for testing."""
    _rate_limit_store.clear()
