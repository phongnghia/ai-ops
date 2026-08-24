"""Structured JSON logging configuration.

Provides a JSON log formatter and a one-time configuration entry point for the
backend service. Every emitted log record carries these standard fields:
``timestamp`` (ISO 8601, UTC), ``level``, ``service``, ``environment``,
``request_id``, and ``message``.

The log level is derived from the deployment environment: ``production``
suppresses ``DEBUG`` output so that sensitive build log content is never
written at debug level. The environment value is supplied by the caller rather
than read here, keeping environment access centralized in the config module.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

DEFAULT_SERVICE_NAME = "ai-ops-log-analyzer"

# Production suppresses DEBUG to avoid leaking sensitive build log content.
PRODUCTION_ENVIRONMENT = "production"

# Placeholder emitted when no request context has been established yet, so the
# request_id field is always present in every log record.
UNSET_REQUEST_ID = "-"

_STANDARD_FIELDS = ("timestamp", "level", "service", "environment", "request_id", "message")

# Standard LogRecord attributes and fields already serialized in the JSON
# envelope. These are excluded when collecting extra= context from a record to
# prevent duplicate keys and CPython logging internals from appearing in logs.
_RESERVED_RECORD_ATTRS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        "service", "environment", "request_id",
    }
)

_request_id_var: ContextVar[str] = ContextVar("request_id", default=UNSET_REQUEST_ID)


def set_request_id(request_id: str) -> None:
    """Bind a request identifier to the current execution context.

    All log records emitted after this call include the given ``request_id``.

    Args:
        request_id: The identifier to attach to subsequent log records.
    """
    _request_id_var.set(request_id)


def get_request_id() -> str:
    """Return the request identifier bound to the current context.

    Returns:
        The current request identifier, or a placeholder if none is set.
    """
    return _request_id_var.get()


class RequestContextFilter(logging.Filter):
    """Injects service, environment, and request_id onto every log record."""

    def __init__(self, service: str, environment: str) -> None:
        """Initialize the filter with the static service identity.

        Args:
            service: Logical service name emitted in the ``service`` field.
            environment: Deployment environment emitted in the ``environment`` field.
        """
        super().__init__()
        self._service = service
        self._environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach standard context fields to the record.

        Args:
            record: The log record being processed.

        Returns:
            Always ``True`` so that no record is filtered out.
        """
        record.service = self._service
        record.environment = self._environment
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


class JsonLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON with the standard field schema."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as a JSON string.

        Args:
            record: The log record to serialize.

        Returns:
            A JSON-encoded string containing the standard fields plus any extra
            context attributes and exception details when present.
        """
        payload: dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "service": getattr(record, "service", DEFAULT_SERVICE_NAME),
            "environment": getattr(record, "environment", ""),
            "request_id": getattr(record, "request_id", UNSET_REQUEST_ID),
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)

    @staticmethod
    def _format_timestamp(created: float) -> str:
        """Format an epoch timestamp as an ISO 8601 UTC string.

        Args:
            created: Epoch seconds from the log record.

        Returns:
            An ISO 8601 timestamp in UTC with a trailing ``Z`` designator.
        """
        moment = datetime.fromtimestamp(created, tz=timezone.utc)
        return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def resolve_log_level(environment: str) -> int:
    """Resolve the effective log level for a deployment environment.

    Args:
        environment: The deployment environment name (e.g. ``production``).

    Returns:
        The ``logging`` level constant to apply.
    """
    if environment.strip().lower() == PRODUCTION_ENVIRONMENT:
        return logging.INFO
    return logging.DEBUG


def configure_logging(
    *,
    environment: str,
    service: str = DEFAULT_SERVICE_NAME,
    level: int | None = None,
) -> None:
    """Configure structured JSON logging for the whole application.

    Installs a single stdout handler on the root logger using the JSON
    formatter and the request-context filter. Safe to call once at startup;
    repeated calls replace the previously installed handlers so configuration
    stays idempotent.

    Args:
        environment: Deployment environment (``APP_ENV``); controls the default
            level and populates the ``environment`` log field.
        service: Logical service name emitted in the ``service`` field.
        level: Explicit log level override; when ``None`` the level is derived
            from ``environment`` via :func:`resolve_log_level`.
    """
    effective_level = level if level is not None else resolve_log_level(environment)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(RequestContextFilter(service=service, environment=environment))

    root_logger = logging.getLogger()
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)
    root_logger.setLevel(effective_level)
