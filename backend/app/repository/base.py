"""Analysis repository abstraction.

Defines :class:`AnalysisRepository`, the persistence boundary for
:class:`~app.models.db_models.AnalysisRecord`. It is expressed as a
:class:`typing.Protocol` so that ``core`` business logic depends on an
abstraction rather than a concrete database implementation.

Concrete implementations are injected into ``core`` via dependency injection.
Because this module only declares an interface, the ORM model is imported under
``TYPE_CHECKING`` and annotations are strings to avoid a runtime import of the
persistence layer from an abstraction module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.models.db_models import AnalysisRecord


@runtime_checkable
class AnalysisRepository(Protocol):
    """Persistence boundary for analysis history used as RAG context.

    Implementations must use parameterized queries for every read and write to
    prevent SQL injection, and must not leak persistence details (sessions,
    query text) to callers in ``core``.
    """

    def save(self, record: AnalysisRecord) -> None:
        """Persist a single analysis record.

        Args:
            record: The fully populated record to store. Callers treat this as
                best-effort persistence; failures are surfaced as exceptions and
                handled by the service layer without blocking the main flow.

        Returns:
            None.
        """
        ...

    def find_similar_by_keyword(
        self,
        keywords: list[str],
        exclude_build: str,
        limit: int,
    ) -> list[AnalysisRecord]:
        """Find similar records by keyword match.

        Args:
            keywords: Salient error tokens extracted from the current cleaned
                log, matched against stored logs.
            exclude_build: Build number of the current analysis, excluded from
                results to avoid self-reference.
            limit: Maximum number of records to return.

        Returns:
            Up to ``limit`` matching records, most relevant first. An empty list
            when nothing matches.
        """
        ...

    def find_similar_by_vector(
        self,
        embedding: list[float],
        exclude_build: str,
        limit: int,
    ) -> list[AnalysisRecord]:
        """Find similar records by vector (semantic) distance.

        Args:
            embedding: Vector embedding of the current cleaned log, compared
                against stored embeddings by nearest-neighbor distance.
            exclude_build: Build number of the current analysis, excluded from
                results to avoid self-reference.
            limit: Maximum number of records to return.

        Returns:
            Up to ``limit`` nearest records, closest first. An empty list when
            nothing matches.
        """
        ...
