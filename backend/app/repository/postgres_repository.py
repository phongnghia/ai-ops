"""PostgreSQL implementation of the analysis repository.

Concrete :class:`~app.repository.base.AnalysisRepository` backed by PostgreSQL
via SQLAlchemy. It persists :class:`~app.models.db_models.AnalysisRecord` rows
and retrieves similar records to build RAG context for new analyses.

Design notes:
- Every read and write uses SQLAlchemy Core/ORM constructs with bound
  parameters — user-supplied values (keywords, build numbers, embeddings) are
  never concatenated into SQL text, preventing SQL injection.
- Keyword search matches ``cleaned_log`` with case-insensitive ``ILIKE`` and
  ranks results by the number of distinct keywords matched, then by recency
  (``created_at DESC``), excluding the current build.
- Vector search orders by pgvector cosine distance using the ``<=>`` operator;
  nearest neighbors come first.
- The session factory is injected via the constructor, keeping this repository
  decoupled from how sessions are created and making it unit-testable.
- Persistence failures surface as ``RepositorySaveError`` / ``RetrievalError``
  so the service layer can degrade gracefully without leaking persistence details.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import reduce

from sqlalchemy import case, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import RepositorySaveError, RetrievalError
from app.db.session import get_session_factory
from app.models.db_models import AnalysisRecord

# ILIKE wildcard wrapper for substring matching. The keyword itself is always
# passed as a bound parameter, so this only shapes matching semantics.
_ILIKE_WILDCARD = "%"


class PostgresAnalysisRepository:
    """PostgreSQL-backed persistence for analysis history (RAG corpus).

    Implements the :class:`~app.repository.base.AnalysisRepository` protocol.
    Each public method manages its own short-lived session obtained from the
    injected factory, so callers in ``core`` never handle sessions directly.
    """

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        """Initialize the repository with an injected session factory.

        Args:
            session_factory: Factory producing new ORM sessions. Defaults to the
                process-wide factory from :func:`app.db.session.get_session_factory`
                when not provided; tests inject a factory bound to a test engine.
        """
        self._session_factory = session_factory or get_session_factory()

    @contextmanager
    def _write_scope(self) -> Iterator[Session]:
        """Yield a session that commits on success and rolls back on failure.

        Yields:
            An active session; committed when the block exits normally, rolled
            back on any exception, and always closed afterwards.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def _read_scope(self) -> Iterator[Session]:
        """Yield a read-only session that is always closed afterwards.

        Deliberately omits commit/rollback — reads are not transactional in
        this repository; adding a transaction would hold a connection open
        longer than needed. Mutations must use :meth:`_write_scope`.

        Yields:
            An active session for read-only queries.
        """
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def save(self, record: AnalysisRecord) -> None:
        """Persist a single analysis record.

        Args:
            record: The fully populated record to store.

        Raises:
            RepositorySaveError: If the database write fails.
        """
        try:
            with self._write_scope() as session:
                session.add(record)
        except SQLAlchemyError as exc:
            raise RepositorySaveError("Failed to persist analysis record") from exc

    def find_similar_by_keyword(
        self,
        keywords: list[str],
        exclude_build: str,
        limit: int,
    ) -> list[AnalysisRecord]:
        """Find similar records by case-insensitive keyword match.

        Ranks candidates by how many of the supplied keywords appear in the
        stored ``cleaned_log`` (descending), breaking ties by recency, and
        excludes the current build.

        Args:
            keywords: Salient error tokens matched against stored logs.
            exclude_build: Current build number, excluded to avoid self-reference.
            limit: Maximum number of records to return.

        Returns:
            Up to ``limit`` matching records, most relevant first.

        Raises:
            RetrievalError: If the query fails or times out.
        """
        cleaned_keywords = [kw for kw in keywords if kw and kw.strip()]
        if not cleaned_keywords or limit <= 0:
            return []

        ilike_conditions = [
            AnalysisRecord.cleaned_log.ilike(
                f"{_ILIKE_WILDCARD}{keyword}{_ILIKE_WILDCARD}"
            )
            for keyword in cleaned_keywords
        ]

        # Build a SQL expression that counts how many keywords appear in cleaned_log:
        # SUM(CASE WHEN cleaned_log ILIKE '%kw1%' THEN 1 ELSE 0 END + ...)
        # reduce() folds the per-keyword CASE expressions into a single additive column.
        match_count = reduce(
            lambda left, right: left + right,
            (case((condition, 1), else_=0) for condition in ilike_conditions),
        )

        statement = (
            select(AnalysisRecord)
            .where(AnalysisRecord.build_number != exclude_build)
            .where(or_(*ilike_conditions))
            .order_by(match_count.desc(), AnalysisRecord.created_at.desc())
            .limit(limit)
        )

        try:
            with self._read_scope() as session:
                return list(session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            raise RetrievalError("Keyword similarity search failed") from exc

    def find_similar_by_vector(
        self,
        embedding: list[float],
        exclude_build: str,
        limit: int,
    ) -> list[AnalysisRecord]:
        """Find similar records by pgvector cosine distance (``<=>``).

        Orders candidates by ascending cosine distance to ``embedding`` (nearest
        first), restricts to rows that have an embedding, and excludes the
        current build.

        Args:
            embedding: Query vector for the current cleaned log.
            exclude_build: Current build number, excluded to avoid self-reference.
            limit: Maximum number of records to return.

        Returns:
            Up to ``limit`` nearest records, closest first.

        Raises:
            RetrievalError: If the query fails or times out.
        """
        if not embedding or limit <= 0:
            return []

        statement = (
            select(AnalysisRecord)
            .where(AnalysisRecord.build_number != exclude_build)
            .where(AnalysisRecord.embedding.isnot(None))
            .order_by(AnalysisRecord.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        try:
            with self._read_scope() as session:
                return list(session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            raise RetrievalError("Vector similarity search failed") from exc
