"""RAG context retrieval for a new analysis request.

Retrieves similar past analyses (RAG context) for the current cleaned log and
assembles them into a single, length-bounded context string that the
``PromptBuilder`` embeds into the user message.

This module defines the :class:`ContextRetriever` abstraction and its two
implementations selected by ``SIMILARITY_SEARCH_MODE``:

- :class:`KeywordContextRetriever` (``keyword`` mode, default): extracts salient
  error keywords from the cleaned log and queries the repository by keyword
  match.
- :class:`VectorContextRetriever` (``vector`` mode): turns the cleaned log into a
  vector embedding via an injected :class:`Embedder` and queries the repository
  by nearest-neighbor (semantic) distance.

The concrete implementation is chosen by :func:`create_context_retriever`, a
factory keyed on configuration. Adding a new mode only requires a new
implementation plus a factory branch, never a change to ``AnalysisService``
(Open/Closed).

Both retrievers share the same assembly and truncation logic via
:class:`_BaseContextRetriever` (DRY). Any failure or timeout is caught, logged
at ``WARN`` level, and turned into an empty context so the main analysis flow
always continues.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.db.config import AppConfig
    from app.models.db_models import AnalysisRecord
    from app.repository.base import AnalysisRepository

logger = logging.getLogger(__name__)

# Empty RAG_Context returned when nothing is found or retrieval fails.
EMPTY_CONTEXT = ""

# Minimum length for a token to be considered a salient keyword. Short tokens
# (e.g. "is", "at", "the") carry little signal for matching similar failures.
MIN_KEYWORD_LENGTH = 4

# Upper bound on the number of keywords extracted from a cleaned log, keeping
# the repository query bounded regardless of log size.
MAX_KEYWORDS = 20

# Dimensionality of the deterministic placeholder embedding used in demo/vector
# mode when no production-grade embedder is injected.
DEFAULT_EMBEDDING_DIM = 16

# Lines matching this pattern (case-insensitive) are treated as error lines and
# preferred as the source of keywords, mirroring the preprocessor's filter.
_ERROR_LINE_PATTERN = re.compile(r"ERROR|FATAL|Exception|Failed", re.IGNORECASE)

# Token pattern for keyword extraction: identifier-like runs including dots and
# underscores so qualified names (e.g. ``java.lang.NullPointerException``) and
# error codes are captured as single keywords.
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.]+")

# \n\n---\n\n separates records so the LLM treats each as a distinct block.
# The --- acts as a visual break; the surrounding blank lines prevent it from
# being interpreted as a setext heading underline for the line above.
_RECORD_SEPARATOR = "\n\n---\n\n"

# Only Root Cause and Fix Steps are included in RAG context — Problem is omitted
# because it tends to be build-specific boilerplate (e.g. "the build failed")
# that adds noise without improving similarity matching.
# Values mirror prompts.py SECTION_ROOT_CAUSE / SECTION_FIX_STEPS.
_SECTION_ROOT_CAUSE = "🔍 Root Cause"
_SECTION_FIX_STEPS  = "🛠️ Fix Steps"
_CONDENSED_SECTIONS = (_SECTION_ROOT_CAUSE, _SECTION_FIX_STEPS)

# Maximum characters kept per individual record in RAG context.
# Keeps each record contribution bounded regardless of how long the stored
# analysis is, reducing token usage without losing diagnostic signal.
_MAX_RECORD_CHARS = 600


def _extract_condensed_analysis(analysis_text: str) -> str:
    """Extract Root Cause and Fix Steps from a stored analysis.

    Reduces token consumption by including only the diagnostic sections rather
    than the full analysis. Falls back to a truncated version of the full text
    when no section labels are found (e.g. legacy records).

    Args:
        analysis_text: Full plain-text analysis stored in the DB.

    Returns:
        Condensed string with Root Cause and Fix Steps only, capped at
        _MAX_RECORD_CHARS characters.
    """
    sections: dict[str, str] = {s: "" for s in _CONDENSED_SECTIONS}
    current: str | None = None

    for line in analysis_text.splitlines():
        stripped = line.strip()
        if stripped in sections:
            current = stripped
            continue
        if current is not None:
            sections[current] = (sections[current] + "\n" + line).lstrip("\n")

    parts = [
        f"{label}\n{content.strip()}"
        for label, content in sections.items()
        if content.strip()
    ]

    condensed = "\n\n".join(parts) if parts else analysis_text
    return condensed[:_MAX_RECORD_CHARS]


class ContextRetriever(Protocol):
    """Abstraction for retrieving RAG context for a cleaned log.

    Implementations select similar past analyses and return them already
    assembled into a single string, truncated to the configured maximum length.
    The ``core`` orchestrator depends on this abstraction rather than a concrete
    search strategy, so new modes can be added without changing the service
    (Open/Closed).
    """

    def retrieve(self, cleaned_log: str, exclude_build: str) -> str:
        """Return the assembled RAG_Context for the given cleaned log.

        Args:
            cleaned_log: The preprocessed build log of the current request.
            exclude_build: Build number of the current analysis, excluded from
                results to avoid self-reference.

        Returns:
            The assembled RAG_Context string, already truncated to the
            configured maximum length. An empty string when no similar records
            are found or when retrieval fails.
        """
        ...


@runtime_checkable
class Embedder(Protocol):
    """Abstraction that turns a cleaned log into a vector embedding.

    Injected into :class:`VectorContextRetriever` so the retriever depends on an
    abstraction rather than a concrete embedding backend (dependency inversion).
    A production deployment can supply an embedder backed by the LLM gateway or
    a dedicated embedding model; the default :func:`default_embedder` is a
    lightweight, deterministic placeholder for demos and tests.
    """

    def __call__(self, text: str) -> list[float]:
        """Return the embedding vector for ``text``.

        Args:
            text: The cleaned log to embed.

        Returns:
            A list of floats representing the embedding.
        """
        ...


def default_embedder(text: str) -> list[float]:
    """Produce a deterministic placeholder embedding for demo/vector mode.

    This is intentionally simple: it hashes the input and maps the digest bytes
    into a fixed-dimension float vector in ``[0, 1]``. It is deterministic and
    dependency-free so vector mode can be exercised end-to-end without a real
    embedding model. Replace via injection with a production embedder for
    meaningful semantic similarity.

    Args:
        text: The cleaned log to embed.

    Returns:
        A :data:`DEFAULT_EMBEDDING_DIM`-dimensional embedding vector.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [byte / 255.0 for byte in digest[:DEFAULT_EMBEDDING_DIM]]


class _BaseContextRetriever:
    """Shared dependencies and assembly logic for context retrievers.

    Holds the injected repository and the record-count/length limits, and owns
    the assembly and truncation of retrieved records so both keyword and vector
    retrievers share one implementation (DRY). Concrete retrievers add only
    their strategy-specific ``retrieve`` method.
    """

    def __init__(
        self,
        repository: "AnalysisRepository",
        top_n: int,
        max_chars: int,
    ) -> None:
        """Initialize the retriever with its dependencies and limits.

        Args:
            repository: Persistence boundary used to find similar records.
            top_n: Maximum number of similar records to include in the context.
            max_chars: Maximum total length of the assembled context in
                characters.
        """
        self._repository = repository
        self._top_n = top_n
        self._max_chars = max_chars

    def _assemble_context(
        self,
        records: list["AnalysisRecord"],
        exclude_build: str,
    ) -> str:
        """Assemble retrieved records into a length-bounded context string.

        Enforces the record-count cap defensively (Property 9), re-applies the
        current-build exclusion in case a repository returns it (Property 10),
        and truncates the joined result to ``max_chars`` (Property 11).

        Args:
            records: Records returned by the repository, most relevant first.
            exclude_build: Build number to exclude defensively from the output.

        Returns:
            The assembled, truncated context string, or an empty string when no
            usable records remain.
        """
        if not records:
            return EMPTY_CONTEXT

        blocks: list[str] = []
        for record in records:
            if len(blocks) >= self._top_n:
                break
            # Defensive re-check: exclusion is primarily the repository's job,
            # but never emit the current build's own record.
            if record.build_number == exclude_build:
                continue
            blocks.append(self._format_record(record))

        if not blocks:
            return EMPTY_CONTEXT

        assembled = _RECORD_SEPARATOR.join(blocks)
        # Cap total length to stay within the LLM payload budget. Truncating
        # the joined string guarantees the bound regardless of individual record
        # sizes.
        return assembled[: self._max_chars]

    @staticmethod
    def _format_record(record: "AnalysisRecord") -> str:
        """Format a single record into a compact labeled context block.

        Extracts only the Root Cause and Fix Steps sections from the stored
        analysis to reduce token usage — the LLM only needs the diagnosis
        pattern, not the full Problem description.

        Args:
            record: The record to format.

        Returns:
            A compact block with build number and condensed analysis.
        """
        analysis = record.analysis_result or ""
        condensed = _extract_condensed_analysis(analysis)
        return f"Build {record.build_number}:\n{condensed}"


class KeywordContextRetriever(_BaseContextRetriever):
    """Keyword-based RAG context retriever (default mode).

    Extracts salient error keywords from the cleaned log and queries the
    repository for similar past analyses via keyword matching. Results are
    capped at ``top_n`` records and assembled into a single string that never
    exceeds ``max_chars`` characters. Any retrieval failure degrades gracefully
    to an empty context.
    """

    def retrieve(self, cleaned_log: str, exclude_build: str) -> str:
        """Retrieve and assemble RAG context for the given cleaned log.

        Extracts keywords, queries the repository (excluding the current build),
        and assembles up to ``top_n`` records into a length-bounded string. On
        any repository error the failure is logged at ``WARN`` level and an
        empty string is returned so the analysis flow continues.

        Args:
            cleaned_log: The preprocessed build log of the current request.
            exclude_build: Build number of the current analysis, excluded from
                results to avoid self-reference.

        Returns:
            The assembled context string truncated to ``max_chars``, or an
            empty string when nothing matches or retrieval fails.
        """
        keywords = self._extract_keywords(cleaned_log)
        if not keywords:
            return EMPTY_CONTEXT

        try:
            records = self._repository.find_similar_by_keyword(
                keywords=keywords,
                exclude_build=exclude_build,
                limit=self._top_n,
            )
        except Exception:
            # Never let a retrieval failure break the main analysis flow.
            # Log at WARN and continue with empty context.
            # The cleaned log is not logged.
            logger.warning(
                "RAG context retrieval failed; continuing without context",
                extra={"event": "RAG_RETRIEVAL_FAILED", "exclude_build": exclude_build},
                exc_info=True,
            )
            return EMPTY_CONTEXT

        return self._assemble_context(records, exclude_build)

    def _extract_keywords(self, cleaned_log: str) -> list[str]:
        """Extract salient, de-duplicated error keywords from the cleaned log.

        Prefers tokens from lines that match error patterns; falls back to the
        whole log when no error line is present. Keywords are lower-cased for
        stable matching, de-duplicated while preserving first-seen order, and
        capped at :data:`MAX_KEYWORDS`.

        Args:
            cleaned_log: The preprocessed build log to extract keywords from.

        Returns:
            An ordered list of unique keywords, possibly empty.
        """
        if not cleaned_log or not cleaned_log.strip():
            return []

        lines = cleaned_log.splitlines()
        error_lines = [line for line in lines if _ERROR_LINE_PATTERN.search(line)]
        source_lines = error_lines if error_lines else lines

        seen: set[str] = set()
        keywords: list[str] = []
        for line in source_lines:
            for token in _TOKEN_PATTERN.findall(line):
                if len(token) < MIN_KEYWORD_LENGTH:
                    continue
                normalized = token.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                keywords.append(normalized)
                if len(keywords) >= MAX_KEYWORDS:
                    return keywords

        return keywords


class VectorContextRetriever(_BaseContextRetriever):
    """Vector-based (semantic) RAG context retriever (``vector`` mode).

    Turns the cleaned log into a vector embedding via the injected
    :class:`Embedder` and queries the repository for the nearest past analyses
    by vector distance (pgvector ``<=>``). Results are capped at ``top_n``
    records and assembled into a single string that never exceeds ``max_chars``
    characters. Any embedding or retrieval failure degrades gracefully to an
    empty context.
    """

    def __init__(
        self,
        repository: "AnalysisRepository",
        top_n: int,
        max_chars: int,
        embedder: Embedder,
    ) -> None:
        """Initialize the retriever with its dependencies, limits and embedder.

        Args:
            repository: Persistence boundary used to find similar records.
            top_n: Maximum number of similar records to include.
            max_chars: Maximum total length of the assembled context.
            embedder: Callable that turns the cleaned log into an embedding
                vector. Injected so the retriever depends on an abstraction,
                not a concrete embedding backend.
        """
        super().__init__(repository, top_n, max_chars)
        self._embedder = embedder

    def retrieve(self, cleaned_log: str, exclude_build: str) -> str:
        """Retrieve and assemble RAG context using semantic similarity.

        Creates an embedding for the cleaned log, queries the repository for
        the nearest records (excluding the current build), and assembles up to
        ``top_n`` records into a length-bounded string. On any embedding or
        repository error the failure is logged at ``WARN`` level and an empty
        string is returned so the analysis flow continues.

        Args:
            cleaned_log: The preprocessed build log of the current request.
            exclude_build: Build number of the current analysis, excluded from
                results to avoid self-reference.

        Returns:
            The assembled context string truncated to ``max_chars``, or an
            empty string when nothing matches or retrieval fails.
        """
        if not cleaned_log or not cleaned_log.strip():
            return EMPTY_CONTEXT

        try:
            embedding = self._embedder(cleaned_log)
            if not embedding:
                return EMPTY_CONTEXT
            records = self._repository.find_similar_by_vector(
                embedding=embedding,
                exclude_build=exclude_build,
                limit=self._top_n,
            )
        except Exception:
            # Graceful degradation: embedding or retrieval failures never break
            # the main analysis flow. Log at WARN and continue with empty context.
            # The cleaned log is not logged.
            logger.warning(
                "RAG vector retrieval failed; continuing without context",
                extra={"event": "RAG_RETRIEVAL_FAILED", "exclude_build": exclude_build},
                exc_info=True,
            )
            return EMPTY_CONTEXT

        return self._assemble_context(records, exclude_build)


def create_context_retriever(
    config: "AppConfig",
    repository: "AnalysisRepository",
    embedder: Embedder | None = None,
) -> ContextRetriever:
    """Build the context retriever selected by configuration.

    Chooses the implementation based on ``config.similarity_search_mode``: a
    :class:`VectorContextRetriever` in ``vector`` mode, otherwise a
    :class:`KeywordContextRetriever`. Centralizing selection here keeps
    ``AnalysisService`` agnostic of search strategy, so adding a new mode does
    not require changing the service (Open/Closed).

    Args:
        config: Validated application configuration providing the search mode
            and RAG limits (``rag_top_n``, ``rag_context_max_chars``).
        repository: Persistence boundary injected into the chosen retriever.
        embedder: Optional embedding callable used only in ``vector`` mode;
            defaults to :func:`default_embedder` when not provided.

    Returns:
        A :class:`ContextRetriever` implementation matching the configured mode.
    """
    if config.is_vector_search:
        return VectorContextRetriever(
            repository=repository,
            top_n=config.rag_top_n,
            max_chars=config.rag_context_max_chars,
            embedder=embedder or default_embedder,
        )

    return KeywordContextRetriever(
        repository=repository,
        top_n=config.rag_top_n,
        max_chars=config.rag_context_max_chars,
    )
