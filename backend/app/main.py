"""FastAPI application bootstrap.

Wires the application together: loads the typed configuration, initializes
structured logging, creates the FastAPI instance, registers feature routers,
and attaches the API exception handlers. This module contains no business
logic — each concern lives in its own layer (``api``, ``core``, ``repository``,
``db``, ``llm``). Adding a new feature means adding a router and registering it
here, without modifying existing feature code.
"""

import logging

from fastapi import FastAPI

from app.api import analyze, health
from app.api.error_handlers import register_exception_handlers
from app.db.config import get_config
from app.logging_config import configure_logging

APP_TITLE = "AI Ops Log Analyzer"
APP_DESCRIPTION = (
    "Analyze failed CI/CD build logs and return plain-text AI diagnostics.\n\n"
    "## Usage\n"
    "1. Open **POST /api/analyze-log** below\n"
    "2. Click **Try it out**\n"
    "3. Pick an example from the dropdown (or write your own)\n"
    "4. Click **Execute** — the analysis is returned in the response body\n\n"
    "## Endpoints\n"
    "| Path | Purpose |\n"
    "| --- | --- |\n"
    "| `POST /api/analyze-log` | Submit a cleaned build log for AI analysis |\n"
    "| `GET /health` | Liveness check |\n"
)
APP_VERSION = "0.1.0"

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Configuration is loaded first so startup fails immediately on invalid
    environment, then structured logging is initialized so that every
    subsequent startup log record is already structured.

    Returns:
        The configured FastAPI application with feature routers and exception
        handlers registered.
    """
    config = get_config()
    configure_logging(environment=config.app_env)

    logger.info(
        "Starting application with configured AI provider",
        extra={
            "event": "APP_STARTUP",
            "app_version": APP_VERSION,
            "ai_provider": config.ai_provider,
            # Keep in sync with the equivalent mapping in analysis_service._complete().
            "provider_label": (
                "Ollama" if config.ai_provider == "ollama"
                else "Google Gemini" if config.ai_provider == "google_gemini"
                else "Azure AI Foundry"
            ),
        },
    )

    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.include_router(health.router)
    app.include_router(analyze.router)
    register_exception_handlers(app)

    return app


app = create_app()
