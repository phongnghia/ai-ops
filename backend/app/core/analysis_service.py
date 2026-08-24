"""Analysis orchestration service.

Coordinates a single log-analysis request end to end: retrieve RAG context,
build the prompt, call the LLM gateway, persist the result best-effort, and
return the analysis.

Dependencies are injected via the constructor (dependency inversion) so the
service depends only on abstractions, never on concrete implementations. This
allows providers and search strategies to be swapped without changing this
logic.

Failure handling follows graceful-degradation principles:
- RAG retrieval failures never break the main flow; they yield an empty context
  and a WARN log.
- Persistence failures never block the response; they yield an ERROR log
  (without the cleaned log) and the analysis is still returned.
- Gateway failures propagate as :class:`~app.core.errors.GatewayError` for the
  API layer to map to HTTP 502.

The ``cleaned_log`` content is never written to logs.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.core import prompt_builder
from app.core.context_retriever import ContextRetriever
from app.core.notification_service import NotificationContext, NotificationService
from app.llm.base import LLMClient, LLMResult
from app.models.db_models import AnalysisRecord
from app.models.dto import AnalysisResult
from app.repository.base import AnalysisRepository

logger = logging.getLogger(__name__)

# Sentinel returned when RAG retrieval degrades gracefully so callers never
# receive None — an empty string integrates cleanly with prompt building.
_EMPTY_RAG_CONTEXT = ""

# Converts perf_counter() seconds to integer milliseconds for structured logs.
_MILLISECONDS_PER_SECOND = 1000


class AnalysisService:
    """Orchestrates RAG retrieval, prompt building, LLM call, and persistence.

    The service composes its injected collaborators into the single-request
    analysis flow and guarantees that non-critical failures (RAG retrieval,
    persistence) degrade gracefully without breaking the response returned to
    the caller.
    """

    def __init__(
        self,
        context_retriever: ContextRetriever,
        llm_client: LLMClient,
        repository: AnalysisRepository,
        notification_service: NotificationService,
    ) -> None:
        """Initialize the service with its injected dependencies.

        Args:
            context_retriever: Abstraction that returns RAG context for a
                cleaned log.
            llm_client: Abstraction used to request completions from the LLM
                gateway.
            repository: Persistence boundary for analysis history.
            notification_service: Sends build failure notifications to
                Teams/Slack after analysis completes.
        """
        self._context_retriever = context_retriever
        self._llm_client = llm_client
        self._repository = repository
        self._notification_service = notification_service

    def analyze(
        self,
        build_number: str,
        cleaned_log: str,
        request_id: str,
        job_name: str = "",
        build_url: str = "",
    ) -> AnalysisResult:
        """Analyze a cleaned build log, persist the result, and send notifications.

        Args:
            build_number: Identifier of the failed build being analyzed.
            cleaned_log: The preprocessed build log to analyze.
            request_id: Correlation identifier for structured logging.
            job_name: CI/CD job name — included in notification messages.
            build_url: Direct URL to the build console — linked in notifications.

        Returns:
            The :class:`AnalysisResult` containing the analysis text and the
            provider that produced it.

        Raises:
            GatewayError: If the LLM gateway cannot produce a usable result.
        """
        rag_context = self._retrieve_context(build_number, cleaned_log, request_id)
        messages = prompt_builder.build(cleaned_log, build_number, rag_context)
        result = self._complete(messages, build_number, request_id)
        self._save_best_effort(build_number, cleaned_log, result, request_id)
        self._notify_best_effort(build_number, job_name, build_url, result, request_id)
        return AnalysisResult(text=result.text, provider=result.provider, model=result.model)

    def _retrieve_context(
        self,
        build_number: str,
        cleaned_log: str,
        request_id: str,
    ) -> str:
        """Retrieve RAG context, degrading to an empty string on any failure.

        The retriever already returns an empty string on internal errors, but
        this defensive wrapper guarantees the main flow continues even if the
        retriever itself raises. The cleaned log is never logged.

        Args:
            build_number: Current build, excluded from results to avoid
                self-reference.
            cleaned_log: The preprocessed build log used to find similar records.
            request_id: Correlation identifier for structured logging.

        Returns:
            The assembled RAG context, or an empty string when retrieval fails.
        """
        try:
            return self._context_retriever.retrieve(
                cleaned_log, exclude_build=build_number
            )
        except Exception:
            logger.warning(
                "RAG context retrieval failed; continuing without context",
                extra={
                    "event": "RAG_RETRIEVAL_FAILED",
                    "build_number": build_number,
                    "request_id": request_id,
                },
                exc_info=True,
            )
            return _EMPTY_RAG_CONTEXT

    def _complete(
        self,
        messages: list[dict],
        build_number: str,
        request_id: str,
    ) -> LLMResult:
        """Call the LLM gateway and log the call duration on success.

        Gateway failures propagate to the caller (and ultimately to HTTP 502);
        only successful calls reach the duration log line. No sensitive content
        is logged.

        Args:
            messages: OpenAI-compatible chat messages to send to the model.
            build_number: Current build, included in the structured log.
            request_id: Correlation identifier for structured logging.

        Returns:
            The :class:`~app.llm.base.LLMResult` returned by the client.

        Raises:
            GatewayError: Propagated from the client when no usable result is
                produced.
        """
        start = time.perf_counter()
        logger.info(
            "Outbound LLM request started",
            extra={
                "event": "LLM_CALL_STARTED",
                "build_number": build_number,
                "request_id": request_id,
                "message_count": len(messages),
            },
        )
        result = self._llm_client.complete(messages)
        duration_ms = int((time.perf_counter() - start) * _MILLISECONDS_PER_SECOND)
        logger.info(
            "Log analysis completed by configured AI provider",
            extra={
                "event": "LLM_CALL_COMPLETED",
                "build_number": build_number,
                "request_id": request_id,
                "provider": result.provider,
                "model": result.model,
                "ai_model": result.model,
                "ai_provider": result.provider,
                # provider is the machine-readable identifier (e.g. "azure_foundry");
            # provider_label is the human-readable display name used in dashboards
            # and log queries where the raw identifier is less readable.
            "provider_label": (
                    "Ollama" if "ollama" in result.provider.lower()
                    else "Google Gemini" if "gemini" in result.provider.lower()
                    else "Azure AI Foundry"
                ),
                "duration_ms": duration_ms,
            },
        )
        return result

    def _save_best_effort(
        self,
        build_number: str,
        cleaned_log: str,
        result: LLMResult,
        request_id: str,
    ) -> None:
        """Persist the analysis record without blocking on failure.

        Builds a fully populated :class:`AnalysisRecord` and attempts to save
        it. Any failure is logged at ``ERROR`` level with ``build_number`` and
        ``request_id`` — never the ``cleaned_log`` content — and swallowed so
        the caller still receives the analysis result.

        Args:
            build_number: Identifier of the analyzed build.
            cleaned_log: The analyzed log, stored in the record for future RAG.
            result: The :class:`~app.llm.base.LLMResult` to persist.
            request_id: Correlation identifier for structured logging.
        """
        record = AnalysisRecord(
            build_number=build_number,
            cleaned_log=cleaned_log,
            analysis_result=result.text,
            provider=result.provider,
            created_at=datetime.now(timezone.utc),
        )
        try:
            self._repository.save(record)
        except Exception:
            logger.error(
                "Failed to persist analysis record",
                extra={
                    "event": "ANALYSIS_RECORD_SAVE_FAILED",
                    "build_number": build_number,
                    "request_id": request_id,
                },
                exc_info=True,
            )

    def _notify_best_effort(
        self,
        build_number: str,
        job_name: str,
        build_url: str,
        result: LLMResult,
        request_id: str,
    ) -> None:
        """Send notifications without blocking on failure.

        Constructs a :class:`NotificationContext` and delegates to the
        notification service. Any failure is logged at WARN level and swallowed
        so the analysis result is always returned to the caller.

        Args:
            build_number: Identifier of the analyzed build.
            job_name: CI/CD job name for notification display.
            build_url: Direct URL to the build console log.
            result: The LLM result containing analysis text and provider info.
            request_id: Correlation identifier for structured logging.
        """
        ctx = NotificationContext(
            job_name=job_name or build_number,
            build_number=build_number,
            build_url=build_url,
            analysis_text=result.text,
            provider=result.provider,
            model=result.model,
            request_id=request_id,
        )
        try:
            self._notification_service.notify(ctx)
        except Exception:
            logger.warning(
                "Notification dispatch failed",
                extra={
                    "event": "NOTIFICATION_DISPATCH_FAILED",
                    "build_number": build_number,
                    "request_id": request_id,
                },
                exc_info=True,
            )
