"""ORM model for persisted analysis history.

Defines the SQLAlchemy 2.0 declarative model :class:`AnalysisRecord`, which
stores every successful CI/CD log analysis. Persisted records form the
retrieval corpus for Retrieval-Augmented Generation (RAG): past analyses
become context for future ones (see Requirements 9.2, 11.2).

The optional ``embedding`` column holds a pgvector vector and is populated only
when similarity search runs in ``vector`` mode (see Requirements 10.3, 11.4).
The pgvector type import is guarded so this module stays importable in
environments where the optional ``pgvector`` dependency is not installed; in
that case the column degrades to a nullable, import-safe placeholder that
carries no vector semantics. Enabling ``vector`` mode requires the pgvector
extension and dependency to be present (delivered via migration 0002).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Dimensionality of the stored Vector_Embedding. Kept as a named constant to
# avoid a magic number and to stay in sync with the vector migration (0002).
# 1536 matches common text-embedding model output sizes; adjust here and in the
# migration together if a different embedding model is adopted.
EMBEDDING_DIMENSIONS = 1536

# Guarded import: prefer pgvector's native column type, but remain importable
# when the optional dependency is absent (e.g. keyword-only demo setups).
try:
    from pgvector.sqlalchemy import Vector

    _EMBEDDING_COLUMN_TYPE = Vector(EMBEDDING_DIMENSIONS)
except ImportError:  # pragma: no cover - depends on optional dependency
    # Fallback keeps the module importable without pgvector installed. This
    # placeholder is never used in production vector mode, where pgvector is
    # required; it exists only so the ORM metadata can be loaded.
    _EMBEDDING_COLUMN_TYPE = Text()


class Base(DeclarativeBase):
    """Declarative base for all ORM models in the application."""


def _utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnalysisRecord(Base):
    """A persisted record of a single CI/CD log analysis.

    Each row captures the cleaned log that was analyzed, the Markdown analysis
    returned by the LLM, and the provider that produced it. Rows are queried
    later to build RAG context for similar failures.
    """

    __tablename__ = "analysis_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    build_number: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    cleaned_log: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_result: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    # Nullable: only populated when similarity search runs in ``vector`` mode.
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        _EMBEDDING_COLUMN_TYPE,
        nullable=True,
    )

    def __repr__(self) -> str:
        """Return a concise, log-safe representation (no cleaned_log content)."""
        return (
            f"AnalysisRecord(id={self.id!r}, "
            f"build_number={self.build_number!r}, "
            f"provider={self.provider!r})"
        )
