"""Enterprise Meet — Structured JSON logging with structlog."""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings

# ── Context Variables ─────────────────────────────────────────────────────────

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


def get_request_id() -> str:
    return request_id_ctx.get() or str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def set_user_id(user_id: str) -> None:
    user_id_ctx.set(user_id)


# ── Processors ────────────────────────────────────────────────────────────────

def add_request_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject request_id and user_id from context vars into every log event."""
    rid = request_id_ctx.get()
    uid = user_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    if uid:
        event_dict["user_id"] = uid
    return event_dict


def add_service_info(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add service name and environment to every log event."""
    event_dict["service"] = "enterprise-meet-api"
    event_dict["env"] = settings.APP_ENV
    return event_dict


# ── Configuration ─────────────────────────────────────────────────────────────

def configure_logging() -> None:
    """Initialize structlog with JSON output and request context injection."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure stdlib logging first
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_service_info,
        add_request_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.DEBUG:
        # Pretty console output in development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output in production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structlog bound logger with the given name."""
    return structlog.get_logger(name)
