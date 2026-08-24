"""Dependency injection wiring (FastAPI providers).

Central composition root for the backend service. This module contains the
factory functions that wire the application's abstractions
(``AnalysisRepository``, ``ContextRetriever``, ``LLMClient``,
``AnalysisService``) to their concrete implementations, and exposes them as
FastAPI dependencies via :func:`fastapi.Depends`.

Keeping all wiring here means ``api`` routes depend only on abstractions and
receive a fully-composed :class:`~app.core.analysis_service.AnalysisService`
through ``Depends`` — routes never construct concrete repositories, clients, or
retrievers themselves.

Each provider is intentionally tiny and single-purpose. FastAPI resolves the
dependency graph by composition, making every collaborator individually
overridable in tests via ``app.dependency_overrides``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.analysis_service import AnalysisService
from app.core.context_retriever import ContextRetriever, create_context_retriever
from app.core.notification_service import NotificationService
from app.db.config import AppConfig, get_config
from app.llm.base import LLMClient
from app.llm.litellm_client import LiteLLMClient
from app.repository.base import AnalysisRepository
from app.repository.postgres_repository import PostgresAnalysisRepository


def get_config_dep() -> AppConfig:
    """Provide the validated application configuration.

    Thin FastAPI-facing wrapper around :func:`app.db.config.get_config` so the
    typed config participates in the dependency graph and can be overridden in
    tests.

    Returns:
        The process-wide, validated :class:`AppConfig`.
    """
    return get_config()


def get_repository() -> AnalysisRepository:
    """Provide the analysis repository implementation.

    Returns:
        A ready-to-use :class:`AnalysisRepository` implementation.
    """
    return PostgresAnalysisRepository()


def get_llm_client(
    config: Annotated[AppConfig, Depends(get_config_dep)],
) -> LLMClient:
    """Provide the LLM gateway client, configured from application config.

    Args:
        config: The validated application configuration, injected by FastAPI.

    Returns:
        A :class:`LLMClient` bound to the configured LiteLLM gateway.
    """
    return LiteLLMClient(
        base_url=config.litellm_base_url,
        api_key=config.litellm_api_key,
        timeout_seconds=config.llm_timeout_seconds,
    )


def get_context_retriever(
    config: Annotated[AppConfig, Depends(get_config_dep)],
    repository: Annotated[AnalysisRepository, Depends(get_repository)],
) -> ContextRetriever:
    """Provide the RAG context retriever selected by configuration.

    Args:
        config: The validated application configuration, injected by FastAPI.
        repository: The persistence boundary injected into the retriever.

    Returns:
        A :class:`ContextRetriever` implementation matching the configured mode.
    """
    return create_context_retriever(config=config, repository=repository)


def get_notification_service(
    config: Annotated[AppConfig, Depends(get_config_dep)],
) -> NotificationService:
    """Provide the notification service bound to the application configuration.

    Args:
        config: The validated application configuration, injected by FastAPI.

    Returns:
        A :class:`NotificationService` ready to send Teams/Slack notifications.
    """
    return NotificationService(config=config)


def get_analysis_service(
    context_retriever: Annotated[ContextRetriever, Depends(get_context_retriever)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    repository: Annotated[AnalysisRepository, Depends(get_repository)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> AnalysisService:
    """Provide the fully composed analysis orchestration service.

    Args:
        context_retriever: RAG context retriever, injected by FastAPI.
        llm_client: LLM gateway client, injected by FastAPI.
        repository: Persistence boundary, injected by FastAPI.
        notification_service: Notification sender, injected by FastAPI.

    Returns:
        A ready-to-use :class:`AnalysisService`.
    """
    return AnalysisService(
        context_retriever=context_retriever,
        llm_client=llm_client,
        repository=repository,
        notification_service=notification_service,
    )
