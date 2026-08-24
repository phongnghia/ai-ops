"""Exception-to-HTTP mapping for the API boundary.

Centralizes how domain and validation failures are translated into HTTP
responses so that route handlers stay free of error-formatting concerns.
Every error response uses the consistent envelope:
``{"ok": false, "error": <CODE>, "message": <human-readable>}``

Two failure categories are handled:

- Request validation (:class:`RequestValidationError`) -> HTTP 422. The handler
  rewrites ``cleaned_log`` messages to expose clear specification wording for
  blank input and oversized input. Missing required fields are reported
  explicitly.
- Gateway failures (:class:`GatewayError`) -> HTTP 502 with a short envelope
  that never exposes stack traces, internal endpoints, or API keys.

The public entry point is :func:`register_exception_handlers`, invoked by
``main.py`` during application startup.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import GatewayError
from app.models.dto import CLEANED_LOG_MAX_LENGTH

logger = logging.getLogger(__name__)

VALIDATION_ERROR_CODE = "VALIDATION_ERROR"
GATEWAY_ERROR_CODE = "GATEWAY_ERROR"

# Generic, non-leaky message for gateway failures. Intentionally avoids
# exposing provider URLs, API keys, or stack traces to the caller.
GATEWAY_ERROR_MESSAGE = "LLM gateway unavailable"

CLEANED_LOG_FIELD = "cleaned_log"
CLEANED_LOG_BLANK_MESSAGE = "cleaned_log must not be empty"
CLEANED_LOG_TOO_LONG_MESSAGE = (
    f"cleaned_log exceeds maximum length of {CLEANED_LOG_MAX_LENGTH} characters"
)

_TYPE_MISSING = "missing"
_TYPE_TOO_LONG = "string_too_long"
_TYPE_TOO_SHORT = "string_too_short"


def _field_name(location: tuple) -> str:
    """Extract the offending field name from a Pydantic error ``loc`` tuple.

    Pydantic's ``loc`` is a path from the model root, e.g. ``("body", "cleaned_log")``.
    The last element is the most specific field name and is the only part exposed
    to clients — parent path segments like "body" or "query" are implementation
    details that callers should not see.

    Args:
        location: The ``loc`` tuple from a single Pydantic error entry.

    Returns:
        The most specific field name available for the error.
    """
    if not location:
        return "request"
    return str(location[-1])


def _describe_error(error: dict) -> dict:
    """Map a single Pydantic error entry to a client-facing detail item.

    Rewrites ``cleaned_log`` messages to match the expected API contract wording
    and reports missing fields explicitly.

    Args:
        error: One entry from :meth:`RequestValidationError.errors`.

    Returns:
        A detail dict containing the ``field`` and a human-readable ``message``.
    """
    error_type = error.get("type", "")
    field = _field_name(error.get("loc", ()))

    if error_type == _TYPE_MISSING:
        return {"field": field, "message": f"{field} field is required"}

    if field == CLEANED_LOG_FIELD:
        if error_type == _TYPE_TOO_LONG:
            return {"field": field, "message": CLEANED_LOG_TOO_LONG_MESSAGE}
        if error_type == _TYPE_TOO_SHORT or CLEANED_LOG_BLANK_MESSAGE in error.get("msg", ""):
            return {"field": field, "message": CLEANED_LOG_BLANK_MESSAGE}

    return {"field": field, "message": error.get("msg", "Invalid value")}


async def _handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate request validation failures into an HTTP 422 envelope.

    Args:
        _request: The incoming request (unused; required by the handler signature).
        exc: The validation error raised while parsing the request body.

    Returns:
        A JSON response with HTTP 422 describing every offending field.
    """
    details = [_describe_error(error) for error in exc.errors()]
    top_message = details[0]["message"] if details else "Request validation failed"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "ok": False,
            "error": VALIDATION_ERROR_CODE,
            "message": top_message,
            "details": details,
        },
    )


async def _handle_gateway_error(_request: Request, _exc: GatewayError) -> JSONResponse:
    """Translate LLM gateway failures into a safe HTTP 502 envelope.

    The exception detail is deliberately not included in the response body to
    avoid leaking internal information.

    Args:
        _request: The incoming request (unused; required by the handler signature).
        _exc: The gateway error raised by the analysis flow.

    Returns:
        A short JSON response with HTTP 502.
    """
    # request_id is not available here — the handler signature only receives
    # Request, not the route-level request_id. The LLM client already logged
    # at ERROR with full context before raising, so this is a lightweight record.
    logger.error("LLM gateway request failed", extra={"error_code": GATEWAY_ERROR_CODE})
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "ok": False,
            "error": GATEWAY_ERROR_CODE,
            "message": GATEWAY_ERROR_MESSAGE,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all API exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application to attach the handlers to.
    """
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(GatewayError, _handle_gateway_error)
