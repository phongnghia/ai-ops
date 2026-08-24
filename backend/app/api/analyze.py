"""Log analysis route.

Exposes ``POST /api/analyze-log`` which accepts a cleaned build log and returns
a plain-text analysis produced by the LLM.

This module is the HTTP boundary only: it validates the request via the
Pydantic DTO (invalid bodies are rejected with HTTP 422 automatically), assigns
a correlation ``request_id``, emits the structured request log, and delegates
all business logic to :class:`~app.core.analysis_service.AnalysisService`
injected through :func:`app.deps.get_analysis_service`. The route contains no
business logic.

Domain failures are not handled here: a
:class:`~app.core.errors.GatewayError` raised by the service propagates to the
application-level exception handler, which maps it to HTTP 502.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from app.core.analysis_service import AnalysisService
from app.deps import get_analysis_service
from app.logging_config import set_request_id
from app.models.dto import AnalyzeLogRequest

logger = logging.getLogger(__name__)

_PLAIN_TEXT_MEDIA_TYPE = "text/plain"

# Converts perf_counter() seconds to integer milliseconds for structured logs.
_MILLISECONDS_PER_SECOND = 1000

router = APIRouter(prefix="/api", tags=["analyze"])

_OPENAPI_EXAMPLES = {
    "python_module_not_found": {
        "summary": "Python ModuleNotFoundError",
        "value": {
            "build_number": "42",
            "job_name": "my-python-service",
            "build_url": "http://jenkins:8080/job/my-python-service/42/console",
            "cleaned_log": (
                "ERROR: Demo dependency installation failed\n"
                "ModuleNotFoundError: No module named 'demo_dependency'\n"
                "Build step failed with exit code 1"
            ),
        },
    },
    "docker_build_failure": {
        "summary": "Docker build failure",
        "value": {
            "build_number": "99",
            "job_name": "my-docker-service",
            "build_url": "http://jenkins:8080/job/my-docker-service/99/console",
            "cleaned_log": (
                "Step 4/8 : RUN pip install -r requirements.txt\n"
                "ERROR: Could not find a version that satisfies the requirement numpy==99.0.0\n"
                "ERROR: No matching distribution found for numpy==99.0.0\n"
                "The command '/bin/sh -c pip install -r requirements.txt' returned a non-zero code: 1"
            ),
        },
    },
    "test_failure": {
        "summary": "Unit test failure",
        "value": {
            "build_number": "7",
            "job_name": "order-service",
            "build_url": "http://jenkins:8080/job/order-service/7/console",
            "cleaned_log": (
                "FAILED tests/test_order.py::test_calculate_total - AssertionError: assert 110.0 == 100.0\n"
                "short test summary info\n"
                "FAILED tests/test_order.py::test_calculate_total\n"
                "1 failed, 42 passed in 3.21s"
            ),
        },
    },
}


@router.post(
    "/analyze-log",
    response_class=PlainTextResponse,
    summary="Analyze a failed build log",
    description=(
        "Accepts a preprocessed CI/CD build log and returns a plain-text analysis "
        "produced by the configured LLM provider.\n\n"
        "**Response headers:**\n"
        "- `X-AI-Provider` — provider that served the request (e.g. `ollama`)\n"
        "- `X-AI-Model` — concrete model used (e.g. `ollama_chat/qwen2.5-coder:7b`)\n"
        "- `X-AI-Request-ID` — correlation ID for tracing logs\n\n"
        "**Error responses:**\n"
        "- `422` — invalid or missing request fields\n"
        "- `502` — LLM gateway unavailable"
    ),
    responses={
        200: {
            "description": "Plain-text analysis of the build failure",
            "content": {"text/plain": {"example": "🚨 Problem\nThe build failed..."}},
        },
        422: {
            "description": "Validation error — missing or invalid fields",
            "content": {
                "application/json": {
                    "example": {
                        "ok": False,
                        "error": "VALIDATION_ERROR",
                        "message": "cleaned_log must not be empty",
                        "details": [{"field": "cleaned_log", "message": "cleaned_log must not be empty"}],
                    }
                }
            },
        },
        502: {
            "description": "LLM gateway unavailable",
            "content": {
                "application/json": {
                    "example": {"ok": False, "error": "GATEWAY_ERROR", "message": "LLM gateway unavailable"},
                }
            },
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": _OPENAPI_EXAMPLES,
                }
            }
        }
    },
)
def analyze_log(
    request: AnalyzeLogRequest,
    http_request: Request,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> PlainTextResponse:
    """Analyze a cleaned build log and return the plain-text analysis.

    Pydantic validates the request body before this handler runs, so malformed
    or invalid payloads are rejected with HTTP 422 automatically. On a valid
    request, a correlation ``request_id`` is generated and bound to the logging
    context, a structured INFO record is emitted (without the ``cleaned_log``
    content), and the request is delegated to the analysis service.

    Args:
        request: The validated request body.
        http_request: The raw FastAPI request used to read client headers.
        service: The analysis orchestrator, injected by FastAPI.

    Returns:
        A ``text/plain`` response (HTTP 200) whose body is the plain-text
        analysis produced by the LLM provider.

    Raises:
        GatewayError: If the LLM gateway cannot produce a usable result. Left
            to propagate to the application exception handler for HTTP 502
            mapping; it is intentionally not caught here.
    """
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    start = time.perf_counter()

    client = http_request.headers.get("x-ai-client", "unknown")

    logger.info(
        "Inbound request received",
        extra={
            "event": "REQUEST_RECEIVED",
            "method": http_request.method,
            "path": "/api/analyze-log",
            "build_number": request.build_number,
            "log_length": len(request.cleaned_log),
            "client": client,
            "request_id": request_id,
        },
    )

    result = service.analyze(
        build_number=request.build_number,
        cleaned_log=request.cleaned_log,
        request_id=request_id,
        job_name=request.job_name,
        build_url=request.build_url,
    )

    duration_ms = int((time.perf_counter() - start) * _MILLISECONDS_PER_SECOND)

    logger.info(
        "Outbound response sent",
        extra={
            "event": "RESPONSE_SENT",
            "method": http_request.method,
            "path": "/api/analyze-log",
            "status_code": 200,
            "build_number": request.build_number,
            "provider": result.provider,
            "model": result.model or "unknown",
            "duration_ms": duration_ms,
            "request_id": request_id,
        },
    )

    return PlainTextResponse(
        content=result.text,
        media_type=_PLAIN_TEXT_MEDIA_TYPE,
        status_code=200,
        headers={
            "X-AI-Provider": result.provider,
            "X-AI-Model": result.model or "unknown",
            "X-AI-Request-ID": request_id,
        },
    )
