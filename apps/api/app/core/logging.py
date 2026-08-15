"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production-hardened structured logging module with sensitive field redaction.
"""
import logging
import json
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable for request correlation ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "cookie", "database_url", "access_key", "secret_key"}


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts sensitive keys from log data dictionaries."""
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            if any(s in key.lower() for s in SENSITIVE_KEYS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_data(value)
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


class JSONLogFormatter(logging.Formatter):
    """Formats log records as structured JSON for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "carpet-style-story-match-api",
            "request_id": request_id_ctx.get("-"),
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_obj.update(redact_sensitive_data(record.extra_fields))

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(app_env: str = "development") -> logging.Logger:
    """Configures application-wide logging handlers and formatters."""
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    if app_env.lower() == "production":
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [req:%(message)s]")
        )

    logger.addHandler(handler)
    return logger


logger = setup_logging()
